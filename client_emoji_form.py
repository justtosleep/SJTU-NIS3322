# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'client_emoji_form.ui'
#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow_emoji(object):
    def setupUi(self, MainWindow_emoji):
        MainWindow_emoji.setObjectName("MainWindow_emoji")
        MainWindow_emoji.resize(217, 216)
        self.centralwidget = QtWidgets.QWidget(MainWindow_emoji)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.widget = QtWidgets.QWidget(self.centralwidget)
        self.widget.setObjectName("widget")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.widget)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.tableWidget_emoji = QtWidgets.QTableWidget(self.widget)
        self.tableWidget_emoji.setRowCount(5)
        self.tableWidget_emoji.setColumnCount(5)
        self.tableWidget_emoji.setObjectName("tableWidget_emoji")
        self.tableWidget_emoji.horizontalHeader().setVisible(False)
        self.tableWidget_emoji.horizontalHeader().setDefaultSectionSize(34)
        self.tableWidget_emoji.horizontalHeader().setMinimumSectionSize(25)
        self.tableWidget_emoji.horizontalHeader().setStretchLastSection(False)
        self.tableWidget_emoji.verticalHeader().setVisible(False)
        self.tableWidget_emoji.verticalHeader().setDefaultSectionSize(34)
        self.tableWidget_emoji.verticalHeader().setHighlightSections(True)
        self.tableWidget_emoji.verticalHeader().setMinimumSectionSize(25)
        self.horizontalLayout_2.addWidget(self.tableWidget_emoji)
        self.horizontalLayout.addWidget(self.widget)
        MainWindow_emoji.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow_emoji)
        QtCore.QMetaObject.connectSlotsByName(MainWindow_emoji)

    def retranslateUi(self, MainWindow_emoji):
        _translate = QtCore.QCoreApplication.translate
        MainWindow_emoji.setWindowTitle(_translate("MainWindow_emoji", "MainWindow"))
