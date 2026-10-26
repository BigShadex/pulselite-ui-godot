# Client Tracker quick-start assets

This folder contains a two-page manual quick-start PDF and four worksheet-preview images for adding a client, logging an invoice, reviewing the dashboard, and planning follow-ups.

The images are cropped from rasterized worksheet print exports and labelled **Fictional sample data | Worksheet preview**. They are not live-app screenshots. The builder does not recreate or edit spreadsheet cells. These assets do not establish Excel or Google Sheets compatibility.

Files:

- `client-tracker-quick-start.pdf`
- `01-add-client.png`
- `02-log-invoice.png`
- `03-dashboard.png`
- `04-follow-ups.png`

## Rebuild

Pass rasterized page exports for the Clients, Invoices, Dashboard, and Follow-ups tabs. The builder scales its crop coordinates to the supplied image dimensions.

```text
python build_guide.py --client-page clients-page.png --invoice-page invoices-page.png --dashboard-page dashboard-page.png --follow-ups-page follow-ups-page.png --output-dir output
```

The output directory receives `client-tracker-quick-start.pdf` and the four PNG previews. The source exports and workbook should remain private; distribute only the guide assets intended for publication.
