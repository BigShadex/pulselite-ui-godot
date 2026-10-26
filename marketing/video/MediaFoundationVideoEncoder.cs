using System;
using System.IO;
using System.Linq;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

public static class MediaFoundationVideoEncoder
{
    private const int MfVersion = 0x00020070;
    private const int MfStartupFull = 0;
    private const uint MfVideoInterlaceProgressive = 2;

    private static readonly Guid MfMtMajorType = new Guid("48eba18e-f8c9-4687-bf11-0a74c9f96a8f");
    private static readonly Guid MfMtSubtype = new Guid("f7e34c9a-42e8-4714-b74b-cb29d72c35e5");
    private static readonly Guid MfMtAvgBitrate = new Guid("20332624-fb0d-4d9e-bd0d-cbf6786c102e");
    private static readonly Guid MfMtInterlaceMode = new Guid("e2724bb8-e676-4806-b4b2-a8d6efb44ccd");
    private static readonly Guid MfMtFrameSize = new Guid("1652c33d-d6b2-4012-b834-72030849a37d");
    private static readonly Guid MfMtFrameRate = new Guid("c459a2e8-3d2c-4e44-b132-fee5156c7bb0");
    private static readonly Guid MfMtPixelAspectRatio = new Guid("c6376a1e-8d0a-4027-be45-6d9a0ad39bb6");
    private static readonly Guid MfMtDefaultStride = new Guid("644b4e48-1e02-4516-b0eb-c01ca9d49ac6");
    private static readonly Guid MfMtFixedSizeSamples = new Guid("b8ebefaf-b718-4e04-b0a9-116775e3321b");
    private static readonly Guid MfMtSampleSize = new Guid("dad3ab78-1990-408b-bce2-eba673dacc10");
    private static readonly Guid MfMediaTypeVideo = new Guid("73646976-0000-0010-8000-00aa00389b71");
    private static readonly Guid MfVideoFormatH264 = new Guid("34363248-0000-0010-8000-00aa00389b71");
    private static readonly Guid MfVideoFormatRgb32 = new Guid("00000016-0000-0010-8000-00aa00389b71");

    public static void EncodeDirectory(string frameDirectory, string outputFile, int fps, int bitrate)
    {
        if (fps < 1 || fps > 60) throw new ArgumentOutOfRangeException("fps");
        if (bitrate < 100000 || bitrate > 8000000) throw new ArgumentOutOfRangeException("bitrate");
        string[] frames = Directory.GetFiles(frameDirectory, "frame-*.png")
            .OrderBy(path => Path.GetFileName(path), StringComparer.Ordinal)
            .ToArray();
        if (frames.Length == 0) throw new InvalidOperationException("No frame-*.png files were found.");
        if (File.Exists(outputFile)) File.Delete(outputFile);

        Check(MfNative.MFStartup(MfVersion, MfStartupFull), "MFStartup");
        IMFSinkWriter writer = null;
        IMFMediaType outputType = null;
        IMFMediaType inputType = null;
        try
        {
            Check(MfNative.MFCreateSinkWriterFromURL(outputFile, IntPtr.Zero, IntPtr.Zero, out writer), "MFCreateSinkWriterFromURL");
            Check(MfNative.MFCreateMediaType(out outputType), "MFCreateMediaType(output)");
            SetGuid(outputType, MfMtMajorType, MfMediaTypeVideo);
            SetGuid(outputType, MfMtSubtype, MfVideoFormatH264);
            SetUInt32(outputType, MfMtAvgBitrate, (uint)bitrate);
            SetUInt32(outputType, MfMtInterlaceMode, MfVideoInterlaceProgressive);
            SetSize(outputType, MfMtFrameSize, 1280, 720, "Set output frame size");
            SetRatio(outputType, MfMtFrameRate, (uint)fps, 1, "Set output frame rate");
            SetRatio(outputType, MfMtPixelAspectRatio, 1, 1, "Set output pixel aspect ratio");
            int streamIndex;
            Check(writer.AddStream(outputType, out streamIndex), "IMFSinkWriter.AddStream");

            Check(MfNative.MFCreateMediaType(out inputType), "MFCreateMediaType(input)");
            SetGuid(inputType, MfMtMajorType, MfMediaTypeVideo);
            SetGuid(inputType, MfMtSubtype, MfVideoFormatRgb32);
            SetUInt32(inputType, MfMtInterlaceMode, MfVideoInterlaceProgressive);
            SetSize(inputType, MfMtFrameSize, 1280, 720, "Set input frame size");
            SetRatio(inputType, MfMtFrameRate, (uint)fps, 1, "Set input frame rate");
            SetRatio(inputType, MfMtPixelAspectRatio, 1, 1, "Set input pixel aspect ratio");
            SetUInt32(inputType, MfMtDefaultStride, 1280u * 4u);
            SetUInt32(inputType, MfMtFixedSizeSamples, 1);
            SetUInt32(inputType, MfMtSampleSize, 1280u * 720u * 4u);
            Check(writer.SetInputMediaType(streamIndex, inputType, IntPtr.Zero), "IMFSinkWriter.SetInputMediaType");
            Check(writer.BeginWriting(), "IMFSinkWriter.BeginWriting");

            long frameDuration = 10000000L / fps;
            for (int index = 0; index < frames.Length; index++)
            {
                byte[] pixels = ReadRgb32(frames[index]);
                IMFSample sample = null;
                IMFMediaBuffer buffer = null;
                try
                {
                    Check(MfNative.MFCreateSample(out sample), "MFCreateSample");
                    Check(MfNative.MFCreateMemoryBuffer(pixels.Length, out buffer), "MFCreateMemoryBuffer");
                    IntPtr data;
                    int maxLength;
                    int currentLength;
                    Check(buffer.Lock(out data, out maxLength, out currentLength), "IMFMediaBuffer.Lock");
                    try
                    {
                        Marshal.Copy(pixels, 0, data, pixels.Length);
                    }
                    finally
                    {
                        Check(buffer.Unlock(), "IMFMediaBuffer.Unlock");
                    }
                    Check(buffer.SetCurrentLength(pixels.Length), "IMFMediaBuffer.SetCurrentLength");
                    IntPtr bufferInterface = Marshal.GetComInterfaceForObject(buffer, typeof(IMFMediaBuffer));
                    try
                    {
                        Check(sample.AddBuffer(bufferInterface), "IMFSample.AddBuffer");
                    }
                    finally
                    {
                        Marshal.Release(bufferInterface);
                    }
                    Check(sample.SetSampleTime(index * frameDuration), "IMFSample.SetSampleTime");
                    Check(sample.SetSampleDuration(frameDuration), "IMFSample.SetSampleDuration");
                    Check(writer.WriteSample(streamIndex, sample), "IMFSinkWriter.WriteSample");
                }
                finally
                {
                    ReleaseComObject(buffer);
                    ReleaseComObject(sample);
                }
            }
            Check(writer.FinalizeWriter(), "IMFSinkWriter.Finalize");
        }
        finally
        {
            ReleaseComObject(inputType);
            ReleaseComObject(outputType);
            ReleaseComObject(writer);
            MfNative.MFShutdown();
        }
    }

    private static byte[] ReadRgb32(string path)
    {
        using (Bitmap source = new Bitmap(path))
        using (Bitmap converted = new Bitmap(1280, 720, PixelFormat.Format32bppRgb))
        using (Graphics graphics = Graphics.FromImage(converted))
        {
            if (source.Width != 1280 || source.Height != 720)
                throw new InvalidDataException("Every Godot viewport frame must be 1280x720.");
            graphics.DrawImage(source, new Rectangle(0, 0, 1280, 720));
            Rectangle rectangle = new Rectangle(0, 0, 1280, 720);
            BitmapData data = converted.LockBits(rectangle, ImageLockMode.ReadOnly, PixelFormat.Format32bppRgb);
            try
            {
                byte[] pixels = new byte[1280 * 720 * 4];
                int rowLength = 1280 * 4;
                int stride = data.Stride;
                for (int row = 0; row < 720; row++)
                {
                    IntPtr sourceRow = IntPtr.Add(data.Scan0, row * stride);
                    Marshal.Copy(sourceRow, pixels, row * rowLength, rowLength);
                }
                return pixels;
            }
            finally
            {
                converted.UnlockBits(data);
            }
        }
    }

    private static void SetGuid(IMFMediaType attributes, Guid key, Guid value)
    {
        Check(attributes.SetGUID(ref key, ref value), "IMFAttributes.SetGUID");
    }

    private static void SetUInt32(IMFMediaType attributes, Guid key, uint value)
    {
        Check(attributes.SetUINT32(ref key, value), "IMFAttributes.SetUINT32");
    }

    private static void SetSize(IMFMediaType attributes, Guid key, uint width, uint height, string operation)
    {
        ulong packedValue = ((ulong)width << 32) | height;
        Check(attributes.SetUINT64(ref key, packedValue), operation);
    }

    private static void SetRatio(IMFMediaType attributes, Guid key, uint numerator, uint denominator, string operation)
    {
        ulong packedValue = ((ulong)numerator << 32) | denominator;
        Check(attributes.SetUINT64(ref key, packedValue), operation);
    }

    private static void Check(int result, string operation)
    {
        if (result < 0)
        {
            throw new COMException(operation + " failed with HRESULT 0x" + result.ToString("X8") + ".", result);
        }
    }

    private static void ReleaseComObject(object value)
    {
        if (value != null && Marshal.IsComObject(value)) Marshal.ReleaseComObject(value);
    }

    private static class MfNative
    {
        [DllImport("mfplat.dll", ExactSpelling = true)] internal static extern int MFStartup(int version, int flags);
        [DllImport("mfplat.dll", ExactSpelling = true)] internal static extern int MFShutdown();
        [DllImport("mfplat.dll", ExactSpelling = true)] internal static extern int MFCreateMediaType(out IMFMediaType mediaType);
        [DllImport("mfplat.dll", ExactSpelling = true)] internal static extern int MFCreateSample(out IMFSample sample);
        [DllImport("mfplat.dll", ExactSpelling = true)] internal static extern int MFCreateMemoryBuffer(int maxLength, out IMFMediaBuffer buffer);
        [DllImport("mfreadwrite.dll", CharSet = CharSet.Unicode, ExactSpelling = true)]
        internal static extern int MFCreateSinkWriterFromURL(string outputPath, IntPtr byteStream, IntPtr attributes, out IMFSinkWriter writer);
    }

    [ComImport, Guid("44ae0fa8-ea31-4109-8d2e-4cae4997c555"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IMFMediaType
    {
        [PreserveSig] int GetItem(ref Guid key, IntPtr value);
        [PreserveSig] int GetItemType(ref Guid key, out int type);
        [PreserveSig] int CompareItem(ref Guid key, IntPtr value, out bool result);
        [PreserveSig] int Compare(IntPtr theirs, int matchType, out bool result);
        [PreserveSig] int GetUINT32(ref Guid key, out uint value);
        [PreserveSig] int GetUINT64(ref Guid key, out ulong value);
        [PreserveSig] int GetDouble(ref Guid key, out double value);
        [PreserveSig] int GetGUID(ref Guid key, out Guid value);
        [PreserveSig] int GetStringLength(ref Guid key, out int length);
        [PreserveSig] int GetString(ref Guid key, IntPtr value, int bufferSize, out int length);
        [PreserveSig] int GetAllocatedString(ref Guid key, out IntPtr value, out int length);
        [PreserveSig] int GetBlobSize(ref Guid key, out int size);
        [PreserveSig] int GetBlob(ref Guid key, IntPtr value, int bufferSize, out int size);
        [PreserveSig] int GetAllocatedBlob(ref Guid key, out IntPtr value, out int size);
        [PreserveSig] int GetUnknown(ref Guid key, ref Guid iid, out IntPtr value);
        [PreserveSig] int SetItem(ref Guid key, IntPtr value);
        [PreserveSig] int DeleteItem(ref Guid key);
        [PreserveSig] int DeleteAllItems();
        [PreserveSig] int SetUINT32(ref Guid key, uint value);
        [PreserveSig] int SetUINT64(ref Guid key, ulong value);
        [PreserveSig] int SetDouble(ref Guid key, double value);
        [PreserveSig] int SetGUID(ref Guid key, ref Guid value);
        [PreserveSig] int SetString(ref Guid key, [MarshalAs(UnmanagedType.LPWStr)] string value);
        [PreserveSig] int SetBlob(ref Guid key, IntPtr value, int size);
        [PreserveSig] int SetUnknown(ref Guid key, [MarshalAs(UnmanagedType.IUnknown)] object value);
        [PreserveSig] int LockStore();
        [PreserveSig] int UnlockStore();
        [PreserveSig] int GetCount(out int count);
        [PreserveSig] int GetItemByIndex(int index, IntPtr key, IntPtr value);
        [PreserveSig] int CopyAllItems(IntPtr destination);
        [PreserveSig] int GetMajorType(out Guid majorType);
        [PreserveSig] int IsCompressedFormat(out bool compressed);
        [PreserveSig] int IsEqual(IMFMediaType other, out int flags);
        [PreserveSig] int GetRepresentation(ref Guid representation, out IntPtr value);
        [PreserveSig] int FreeRepresentation(ref Guid representation, IntPtr value);
    }

    [ComImport, Guid("c40a00f2-b93a-4d80-ae8c-5a1c634f58e4"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IMFSample
    {
        [PreserveSig] int GetItem(ref Guid key, IntPtr value);
        [PreserveSig] int GetItemType(ref Guid key, out int type);
        [PreserveSig] int CompareItem(ref Guid key, IntPtr value, out bool result);
        [PreserveSig] int Compare(IntPtr theirs, int matchType, out bool result);
        [PreserveSig] int GetUINT32(ref Guid key, out uint value);
        [PreserveSig] int GetUINT64(ref Guid key, out ulong value);
        [PreserveSig] int GetDouble(ref Guid key, out double value);
        [PreserveSig] int GetGUID(ref Guid key, out Guid value);
        [PreserveSig] int GetStringLength(ref Guid key, out int length);
        [PreserveSig] int GetString(ref Guid key, IntPtr value, int bufferSize, out int length);
        [PreserveSig] int GetAllocatedString(ref Guid key, out IntPtr value, out int length);
        [PreserveSig] int GetBlobSize(ref Guid key, out int size);
        [PreserveSig] int GetBlob(ref Guid key, IntPtr value, int bufferSize, out int size);
        [PreserveSig] int GetAllocatedBlob(ref Guid key, out IntPtr value, out int size);
        [PreserveSig] int GetUnknown(ref Guid key, ref Guid iid, out IntPtr value);
        [PreserveSig] int SetItem(ref Guid key, IntPtr value);
        [PreserveSig] int DeleteItem(ref Guid key);
        [PreserveSig] int DeleteAllItems();
        [PreserveSig] int SetUINT32(ref Guid key, uint value);
        [PreserveSig] int SetUINT64(ref Guid key, ulong value);
        [PreserveSig] int SetDouble(ref Guid key, double value);
        [PreserveSig] int SetGUID(ref Guid key, ref Guid value);
        [PreserveSig] int SetString(ref Guid key, [MarshalAs(UnmanagedType.LPWStr)] string value);
        [PreserveSig] int SetBlob(ref Guid key, IntPtr value, int size);
        [PreserveSig] int SetUnknown(ref Guid key, [MarshalAs(UnmanagedType.IUnknown)] object value);
        [PreserveSig] int LockStore();
        [PreserveSig] int UnlockStore();
        [PreserveSig] int GetCount(out int count);
        [PreserveSig] int GetItemByIndex(int index, IntPtr key, IntPtr value);
        [PreserveSig] int CopyAllItems(IntPtr destination);
        [PreserveSig] int GetSampleFlags(out uint flags);
        [PreserveSig] int SetSampleFlags(uint flags);
        [PreserveSig] int GetSampleTime(out long time);
        [PreserveSig] int SetSampleTime(long time);
        [PreserveSig] int GetSampleDuration(out long duration);
        [PreserveSig] int SetSampleDuration(long duration);
        [PreserveSig] int GetBufferCount(out int count);
        [PreserveSig] int GetBufferByIndex(int index, out IMFMediaBuffer buffer);
        [PreserveSig] int ConvertToContiguousBuffer(out IMFMediaBuffer buffer);
        [PreserveSig] int AddBuffer(IntPtr buffer);
        [PreserveSig] int RemoveBufferByIndex(int index);
        [PreserveSig] int RemoveAllBuffers();
        [PreserveSig] int GetTotalLength(out int length);
        [PreserveSig] int CopyToBuffer(IMFMediaBuffer buffer);
    }

    [ComImport, Guid("045fa593-8799-42b8-bc8d-8968c6453507"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IMFMediaBuffer
    {
        [PreserveSig] int Lock(out IntPtr buffer, out int maxLength, out int currentLength);
        [PreserveSig] int Unlock();
        [PreserveSig] int GetCurrentLength(out int length);
        [PreserveSig] int SetCurrentLength(int length);
        [PreserveSig] int GetMaxLength(out int length);
    }

    [ComImport, Guid("3137f1cd-fe5e-4805-a5d8-fb477448cb3d"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IMFSinkWriter
    {
        [PreserveSig] int AddStream(IMFMediaType targetType, out int streamIndex);
        [PreserveSig] int SetInputMediaType(int streamIndex, IMFMediaType inputType, IntPtr encodingParameters);
        [PreserveSig] int BeginWriting();
        [PreserveSig] int WriteSample(int streamIndex, IMFSample sample);
        [PreserveSig] int SendStreamTick(int streamIndex, long timestamp);
        [PreserveSig] int PlaceMarker(int streamIndex, IntPtr markerValue);
        [PreserveSig] int NotifyEndOfSegment(int streamIndex);
        [PreserveSig] int Flush(int streamIndex);
        [PreserveSig] int FinalizeWriter();
    }
}
