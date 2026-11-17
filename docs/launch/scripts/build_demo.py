"""Build the sample PDFs used by the isolated bank recording page."""
from pathlib import Path


def statement(month, days, balance):
    text = ('BT /F1 22 Tf 60 730 Td (NORTHLINE ACCOUNT STATEMENT) Tj '
            '0 -40 Td /F1 12 Tf (Sample document. No real account data.) Tj '
            '0 -55 Td (Maya Bennett - Everyday chequing ending 4821) Tj '
            f'0 -30 Td (Statement period: {month} 1 to {month} {days}, 2026) Tj '
            f'0 -30 Td (Closing balance: {balance} CAD) Tj ET')
    objects = [
        '<< /Type /Catalog /Pages 2 0 R >>',
        '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        f'<< /Length {len(text.encode())} >>\nstream\n{text}\nendstream',
    ]
    data = b'%PDF-1.4\n'
    offsets = []
    for i, item in enumerate(objects, 1):
        offsets.append(len(data))
        data += f'{i} 0 obj\n{item}\nendobj\n'.encode()
    xref = len(data)
    data += ('xref\n0 6\n0000000000 65535 f \n'
             + ''.join(f'{offset:010d} 00000 n \n' for offset in offsets)
             + f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n').encode()
    return data


if __name__ == '__main__':
    destination = Path(__file__).resolve().parents[1] / 'demo' / 'statements'
    destination.mkdir(exist_ok=True)
    for month, days, balance in [('October', 31, '3,248.50'),
                                 ('September', 30, '2,956.81'),
                                 ('August', 31, '2,713.94')]:
        (destination / f'{month}-2026-statement.pdf').write_bytes(statement(month, days, balance))
