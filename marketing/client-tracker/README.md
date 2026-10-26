# Client Tracker preview assets

These previews use the fictional sample workbook. The dashboard and worksheet panels were exported from LibreOffice Calc 26.8.1.1 as PDF pages, then cropped and captioned. They are worksheet previews, not live-app screenshots.

The before/after sequence compares the original sample with a disposable copy containing one fictional Lead entry dated 26 October 2026. No typing was recorded. The invoice panel shows existing fictional Overdue and Open examples from the workbook. The GIF is silent and simulates a sequence of worksheet exports; it is not a recording of a person using the workbook.

## Rebuild

Keep the source sample unchanged. Export a disposable copy separately after entering one fictional client in the next available Clients row, within the template's 300-record limit. Recalculate and save that copy in LibreOffice Calc. Export both source and demo copies to PDF, and rasterize page 2 (Dashboard), page 4 (Clients), and page 22 (Invoices) at 130 DPI. These page numbers follow the workbook's current print layout.

Run the crop-and-caption builder with the five page images and an output directory:

```text
python build_previews.py \
  --dashboard-before <source-dashboard.png> \
  --dashboard-after <demo-dashboard.png> \
  --clients-before <source-clients.png> \
  --clients-after <demo-clients.png> \
  --invoices <demo-invoices.png> \
  --output-dir <output-directory>
```

The builder crops the supplied worksheet renders and adds captions. It does not recreate or edit workbook cells. Keep input workbooks and intermediate PDFs private; only the three PNG previews and silent GIF belong in this folder.

## Verification limits

The exact native Calc copy used for the after-state PDF was checked separately from earlier working copies. Its saved Dashboard values match the previews, its 8,169 formula-cell addresses and workbook feature counts match the source, and its saved formula-error scan found no errors. Calc changed the text of some formulas on save; this is not a claim of full formula equivalence or cross-application compatibility. The original paid workbook was unchanged.

The workbook has a 300-record limit per data tab; extra rows are outside the template's linked ranges. The previews do not establish Excel or Google Sheets compatibility. Excel, Google Sheets, live GUI input, dropdown interaction, and audio were not tested for these assets. The displayed names and contact details are fictional.
