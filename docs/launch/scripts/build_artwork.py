"""Create the README banner and confirmation image from v2 captures."""
import os
from pathlib import Path
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter
from PySide6.QtWidgets import QApplication

P = Path(__file__).resolve().parents[1]
A = P / 'assets'
OUT = P.parent / 'assets'


def label(painter, text, x, y, size, weight=QFont.Weight.Medium):
    font = QFont('Outfit'); font.setPixelSize(size); font.setWeight(weight)
    painter.setFont(font); painter.setPen(QColor('#222b36')); painter.drawText(x,y,text)


def main():
    app = QApplication.instance() or QApplication([])
    assert QFontDatabase.addApplicationFont(str(A / 'fonts/Outfit.ttf')) != -1
    OUT.mkdir(exist_ok=True)
    banner = QImage(1800, 820, QImage.Format.Format_RGB32); banner.fill(QColor('#eef2f5'))
    painter = QPainter(banner); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    bank=QImage(str(A/'browser/bank-page-idle.png')); assert not bank.isNull()
    painter.drawImage(QRectF(710,55,1030,643.75), bank)
    label(painter,'Nudge',100,175,130,QFont.Weight.DemiBold)
    label(painter,'Desktop tasks.',105,310,64)
    label(painter,'Fewer precise clicks.',105,390,60)
    bar=QImage(str(A/'browser/bank-idle.png')); assert not bar.isNull()
    painter.drawImage(QRectF(100,490,1600,1600*bar.height()/bar.width()),bar)
    painter.end(); assert banner.save(str(OUT/'nudge-banner.png'))
    panel=QImage(str(A/'browser/mail-confirm.png')); assert not panel.isNull()
    canvas=QImage(panel.width()+100,panel.height()+100,QImage.Format.Format_RGB32);canvas.fill(QColor('#11151b'))
    painter=QPainter(canvas);painter.drawImage(50,50,panel);painter.end()
    assert canvas.save(str(OUT/'confirmation.png'))
    print('Created static README artwork.')


if __name__=='__main__':
    main()
