# -*- coding: utf-8 -*-
import sys, os, glob

# try:
#         from PySide import QtCore, QtGui
# except ImportError:
from PyQt4 import QtCore, QtGui
QtCore.Slot=QtCore.pyqtSlot
QtCore.Signal=QtCore.pyqtSignal
QtCore.Property=QtCore.pyqtProperty

def genSupportedExtensionList():
    formats = QtGui.QImageReader().supportedImageFormats()
    return [str(x)[2:-1] for x in formats]

SUPPORTED_EXT = genSupportedExtensionList()

# QListWidget
class ImageFileList(QtCore.QObject):
    def __init__(self):
        super(ImageFileList, self).__init__()

        self.sortBy='Name'

        # if argv exist, set dirPath according to it. Else, use getcwd()
        if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
            self._dirPath = os.path.dirname(os.path.realpath(sys.argv[1]))
            self.currentImage=self.imageList.index(os.path.abspath(sys.argv[1]))
        else:
            self._dirPath = os.getcwd()
            self.currentImage=0  # 如果檔案不是圖檔該怎麼處理？或者有些檔案其實是圖檔但沒有副檔名？

        self.genImagesList()

    def genImagesList(self):
        images = []
        for extension in SUPPORTED_EXT:
            pattern=os.path.join(self._dirPath, "*.%s" % extension)
            images.extend(glob.glob(pattern))
        if self.sortBy == 'Name':
            images.sort()
        elif self.sortBy == 'Time':
            images.sort(key=lambda x: os.path.getmtime(x))

        self.imageList=images # [FIXME]如果當前目錄沒有任何圖片，就不要啟動app


class MainWindow(QtGui.QWidget):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.image_lst = ImageFileList()
        self.printer = QtGui.QPrinter()

        class ImageLabel(QtGui.QLabel):
            def __init__(self, scrollAreaInstance):
                super(ImageLabel, self).__init__()
                self.setStyleSheet("QLabel { background-color: #000; color: #eee}")
                self.setAlignment(QtCore.Qt.AlignCenter)
                self.scrollAreaInstance = scrollAreaInstance

            def mousePressEvent(self, event):
                self.__mouseOriginalX = None
                self.__mouseOriginalY = None
                if event.button() == QtCore.Qt.LeftButton:
                    self.__mouseOriginalX = event.globalX()
                    self.__mouseOriginalY = event.globalY()

                super(ImageLabel, self).mousePressEvent(event)

            def mouseMoveEvent(self, event):
                if event.buttons() == QtCore.Qt.LeftButton:
                    currentX = event.globalX()
                    currentY = event.globalY()
                    barX = self.scrollAreaInstance.horizontalScrollBar()
                    barY = self.scrollAreaInstance.verticalScrollBar()
                    barX.setValue(barX.value() - (currentX - self.__mouseOriginalX))
                    barY.setValue(barY.value() - (currentY - self.__mouseOriginalY))

                    self.__mouseOriginalX = currentX
                    self.__mouseOriginalY = currentY

                super(ImageLabel, self).mousePressEvent(event)


        self.scroll_area = QtGui.QScrollArea()
        self.image_label = ImageLabel(self.scroll_area)
        self.scroll_area.setStyleSheet("QLabel { background-color: #000; color: #eee}")
        self.scroll_area.setWidget(self.image_label)

        self.scroll_area.setWidgetResizable(True) # Magic

        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QtGui.QFrame.NoFrame) # Thanks for lzh~
        self.scroll_area.horizontalScrollBar().setSingleStep(20)
        self.scroll_area.verticalScrollBar().setSingleStep(20)

        layout = QtGui.QVBoxLayout()
        layout.setMargin(0)
        layout.setSpacing(0)
        layout.addWidget(self.scroll_area)

        self.setLayout(layout)

        self.setWindowTitle("jkbiv")
        self.setStyleSheet("QLabel { background-color: #000; color: #eee}")
        self.resize(500,400)

#         self.status_bar = QtGui.QStatusBar(self)
#         self.setStatusBar(self.status_bar)
#         self.updateStatusBar()
        self.notify_label =QtGui.QLabel("", self)
        self.notify_label.setStyleSheet('''color:#fff;
        background-color:rgba(0,0,0,100);
        border:1px solid #fff;
        border-radius:3px;
        text-align:center;''')
        self.notify_label.setAlignment(QtCore.Qt.AlignCenter)
        self.notify_label.hide()

        self.scaleNum = 1.0
        self.zoomMode = 'fitToWindow'
        self.rememberZoomMode = False
        self.refreshImage()

        QtGui.QShortcut(QtGui.QKeySequence("q"), self, self.close)
        QtGui.QShortcut(QtGui.QKeySequence("Right"), self, self.smartRight)
        QtGui.QShortcut(QtGui.QKeySequence("Left"), self, self.smartLeft)
        QtGui.QShortcut(QtGui.QKeySequence("Up"), self, self.smartUp)
        QtGui.QShortcut(QtGui.QKeySequence("Down"), self, self.smartDown)
        QtGui.QShortcut(QtGui.QKeySequence("PgDown"), self, self.nextImage)
        QtGui.QShortcut(QtGui.QKeySequence("PgUp"), self, self.prevImage)
        QtGui.QShortcut(QtGui.QKeySequence("s"), self, self.sortSwitcher)
        QtGui.QShortcut(QtGui.QKeySequence("f"), self, self.toggleFullScreen)
        QtGui.QShortcut(QtGui.QKeySequence("="), self, self.zoomIn)
        QtGui.QShortcut(QtGui.QKeySequence("-"), self, self.zoomOut)
        QtGui.QShortcut(QtGui.QKeySequence("1"), self, self.origianlSize)
        QtGui.QShortcut(QtGui.QKeySequence("w"), self, self.fitToWindow)
        QtGui.QShortcut(QtGui.QKeySequence("r"), self, self.toggleRememberZoomMode)
        QtGui.QShortcut(QtGui.QKeySequence("Shift+Right"), self, self.scrollRight)
        QtGui.QShortcut(QtGui.QKeySequence("Shift+Left"), self, self.scrollLeft)
        QtGui.QShortcut(QtGui.QKeySequence("Shift+Up"), self, self.scrollUp)
        QtGui.QShortcut(QtGui.QKeySequence("Shift+Down"), self, self.scrollDown)


    def resizeEvent(self, resizeEvent): # Qt
        # [FIXME]如果目前縮放模式不是fit to window，記得不要resize image_label
#        self.image_label.resize(self.size())
        self.refreshImage()

    def refreshImage(self):
        self.image = QtGui.QPixmap(self.image_lst.imageList[self.image_lst.currentImage])

        if self.zoomMode == 'fitToWindow':
            if self.image.width() < self.scroll_area.width() and self.image.height() < self.scroll_area.height():
                self.image_label.setPixmap(self.image)
                self.scaledImage = self.image
            else:
                self.scaledImage = self.image.scaled(self.scroll_area.size(),
                                                QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                self.image_label.setPixmap(self.scaledImage)
        else: # self.zoomMode == 'free'
            self.scaledImage = self.image.scaled(self.image.size() * self.scaleNum,
                                            QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.image_label.setPixmap(self.scaledImage)
        self.scaleNum = self.scaledImage.width() / self.image.width()
        # 記得更新title的檔名

    def scalePercentage(self):
        return "{percent:.0%}".format(percent=self.scaleNum)

    def fitToWindow(self):
        self.zoomMode = 'fitToWindow'
        self.sendNotify("Fit to Window (%s)" % self.scalePercentage(), 500)
        self.refreshImage()

    def origianlSize(self):
        self.zoomMode = 'free'
        self.scaleNum = 1
        self.sendNotify("Original Size (100%)", 500)
        self.refreshImage()

    def zoomIn(self):
        self.zoomMode = 'free'
        self.scaleNum *= 1.1
        self.sendNotify(self.scalePercentage(), 500)
        self.refreshImage()

    def zoomOut(self):
        self.zoomMode = 'free'
        self.scaleNum *= 0.9
        self.sendNotify(self.scalePercentage(), 500)
        self.refreshImage()

    def toggleRememberZoomMode(self):
        self.rememberZoomMode = not(self.rememberZoomMode)
        self.sendNotify("Remenber Zoom Mode" if self.rememberZoomMode else "Don't Remember Zoom Mode")

    def scrollRight(self, step = 20):
        bar=self.scroll_area.horizontalScrollBar()
        bar.setValue(bar.value() + step)

    def scrollLeft(self, step = 20):
        bar=self.scroll_area.horizontalScrollBar()
        bar.setValue(bar.value() - step)

    def scrollUp(self, step = 20):
        bar=self.scroll_area.verticalScrollBar()
        bar.setValue(bar.value() - step)

    def scrollDown(self, step = 20):
        bar=self.scroll_area.verticalScrollBar()
        bar.setValue(bar.value() + step)

    def ifScaledImageIsSmall(self):
        if self.scaledImage.height() < self.scroll_area.height() + 2 and self.scaledImage.width() < self.scroll_area.width() + 2:
            return True
        else:
            return False

    def smartRight(self):
        if self.ifScaledImageIsSmall():
            self.nextImage()
        else:
            self.scrollRight()

    def smartLeft(self):
        if self.ifScaledImageIsSmall():
            self.prevImage()
        else:
            self.scrollLeft()

    def smartUp(self):
        if self.ifScaledImageIsSmall():
            self.prevImage()
        else:
            self.scrollUp()

    def smartDown(self):
        if self.ifScaledImageIsSmall():
            self.nextImage()
        else:
            self.scrollDown()

    def nextImage(self):
        if 1 + self.image_lst.currentImage == len(self.image_lst.imageList):
            self.image_lst.currentImage = 0
            self.sendNotify("Last document reached, continuing on first document.")
        else:
            self.image_lst.currentImage += 1

        if not(self.rememberZoomMode):
            self.zoomMode = 'fitToWindow'

        self.refreshImage()

    def prevImage(self):
        if self.image_lst.currentImage == 0:
            self.image_lst.currentImage = len(self.image_lst.imageList) - 1
            self.sendNotify("First document reached, continuing on last document.")
        else:
            self.image_lst.currentImage -= 1

        if not(self.rememberZoomMode):
            self.zoomMode = 'fitToWindow'

        self.refreshImage()

    def sortByName(self):
        # Because image_lst.currentImage is just a integer, after re-sort the list,
        # you will get wrong picture with the old integer.
        filename=self.image_lst.imageList[self.image_lst.currentImage]
        self.image_lst.sortBy='Name'
        self.image_lst.genImagesList()
        self.image_lst.currentImage = self.image_lst.imageList.index(filename)
        self.sendNotify("Sorting by Name")

    def sortByTime(self):
        filename=self.image_lst.imageList[self.image_lst.currentImage]
        self.image_lst.sortBy='Time'
        self.image_lst.genImagesList()
        self.image_lst.currentImage = self.image_lst.imageList.index(filename)
        self.sendNotify("Sorting by Time")

    def sortSwitcher(self):
        if self.image_lst.sortBy == 'Time':
            self.sortByName()
        else:
            self.sortByTime()

    def toggleFullScreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.sendNotify("Fullscreen off")
        else:
            self.showFullScreen()
            self.sendNotify("Fullscreen on")

    def paintEvent(self, event): # Qt
        w = self.notify_label.width()
        h = self.notify_label.height()

        x = (self.rect().width()  - w)/2.0
        y = (self.rect().height() - h)/2.0
        self.notify_label.setGeometry(x,y,w,h)

    def sendNotify(self, string, duration = 2000):
        label = self.notify_label
        label.setText(string)
        label.adjustSize()
        x = label.width() + 20
        y = label.height() + 10
        label.resize(x, y)
        label.show()
        QtCore.QTimer.singleShot(duration, lambda: label.hide())


app = QtGui.QApplication(sys.argv)
main_window = MainWindow()
main_window.show()
app.exec_()

# print(main_window.image_lst.imageList)
