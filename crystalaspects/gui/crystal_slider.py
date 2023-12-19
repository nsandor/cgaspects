# ==> GUI Engine imports
from re import L
from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtWidgets import QMainWindow, QMessageBox, QFileDialog

# ==> Non-GUI imports
import numpy as np
import pandas as pd
import os
from pathlib import Path
from collections import defaultdict
from natsort import natsorted

# ==> Local imports
from gui.load_ui import Ui_MainWindow
from utils.shape_analysis import CrystalShape


class create_slider(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

    # Read Summary file
    def read_summary(self):

        # Select summary file and read in as a Dataframe
        summary_file = QFileDialog.getOpenFileName(None, "Read Summary File")
        summary_file = Path(summary_file[0])
        print(summary_file)

        summ_df = pd.read_csv(summary_file)
        if list(summ_df.columns)[-1].startswith("Unnamed"):
            summ_df = summ_df.iloc[:, 1:-1]
        else:
            summ_df = summ_df.iloc[:, 1:]
        print(summ_df)
        self.output_textBox_3.append(summ_df.to_string())

        column_names = list(summ_df)
        print("columns", column_names)

        # Create dictionary to store the change in variables (tile/interaction energies)
        var_dict = defaultdict(list)

        # Records the variable values from summary file
        for column in column_names:
            for index, row in summ_df.iterrows():
                if row[str(column)] not in var_dict[column]:
                    var_dict[column].append(row[str(column)])

        print(var_dict)
        self.output_textBox_3.append(str(var_dict))

        var = len(column_names)
        iteration_list = []
        slider_list = []
        dspinbox_list = []

        for i in range(var):
            print("Adding Varible Sliders")
            label_name = f"varSlider_name_{i+1}"
            name = column_names[i]
            slider = f"varSlider_{i+1}"
            dspinbox = f"spinBox_{i+1}"
            min_var = var_dict[column_names[i]][0]
            min_percent = int(min_var * 100)
            max_var = var_dict[column_names[i]][-1]
            max_percent = int(max_var * 100)
            print("min:", min_var)
            print("max:", max_var)
            iteration = var_dict[column_names[i]][1] - var_dict[column_names[i]][0]
            iteration = float("{:.2f}".format(iteration))
            iteration_list.append(iteration)
            print(iteration)
            self.label_name = QtWidgets.QLabel(self.tab_3d)
            font = QtGui.QFont()
            font.setFamily("Arial")
            self.label_name.setFont(font)
            self.label_name.setObjectName(label_name)
            self.label_name.setText(str(name))
            self.E_variables_layout.addWidget(self.label_name, i, 0, 1, 1)
            self.slider = QtWidgets.QSlider(self.tab_3d)
            self.slider.setOrientation(QtCore.Qt.Horizontal)
            self.slider.setObjectName(slider)
            self.slider.setMinimum(min_percent)
            self.slider.setMaximum(max_percent)
            self.slider.setTickInterval(int(iteration * 100))
            slider_list.append(self.slider)

            try:
                self.slider.valueChanged.connect(
                    lambda: self.slider_change(
                        var=var,
                        slider_list=slider_list,
                        dspinbox_list=dspinbox_list,
                        summ_df=summ_df,
                        crystals=self.xyz_files,
                    )
                )
            except NameError:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setText("Please load in the images first!")
                msg.setInformativeText(
                    "You have not loaded in the images, please use the 'Open Images Folder' Button to load in the images first."
                )
                msg.setWindowTitle("Error: No Images Found!")
                msg.exec_()
            self.E_variables_layout.addWidget(self.slider, i, 1, 1, 1)
            self.dspinbox = QtWidgets.QDoubleSpinBox(self.tab_3d)
            self.dspinbox.setObjectName(dspinbox)
            self.dspinbox.setMinimum(min_var)
            self.dspinbox.setMaximum(max_var)
            self.dspinbox.setSingleStep(iteration)
            dspinbox_list.append(self.dspinbox)
            self.dspinbox.valueChanged.connect(
                lambda: self.dspinbox_change(
                    var=var,
                    dspinbox_list=dspinbox_list,
                    slider_list=slider_list,
                )
            )
            self.E_variables_layout.addWidget(self.dspinbox, i, 2, 1, 1)

        self.progressBar.setValue(100)
        self.statusBar().showMessage("Complete: Summary file read in!")

    def read_crystals(self):

        self.crystal_num = 0

        self.statusBar().showMessage("Reading Images...")

        xyz_folderpath = QFileDialog.getExistingDirectory(
            None, "Select Folder that contains the Crystal Outputs (.XYZ)"
        )
        xyz_folderpath = Path(xyz_folderpath)

        try:
            self.crystal_xyz_list = list(xyz_folderpath.rglob("*.XYZ"))
        except Exception as exc:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText(
                f"Please make sure the folder you have selected \
                contains XYZ files that are from the simulation(s)\
                \n Python Error: {repr(exc)}"
            )
            msg.setWindowTitle("Error! No XYZ files detected.")
            msg.exec_()

        for item in self.crystal_xyz_list:
            if Path(item).name.startswith("._"):
                self.crystal_xyz_list.remove(item)

        self.crystal_xyz_list = natsorted(self.crystal_xyz_list)
        print(self.crystal_xyz_list)
        self.output_textBox_3.append(
            f"Number of Images found: {str(len(self.crystal_xyz_list))}"
        )
        self.statusBar().showMessage("Complete: Image data read in!")

        return (xyz_folderpath, self.crystal_xyz_list)

    def get_xyz_info(self, filepath):
        with open(filepath, 'r') as file:
            lines = file.readlines()
            num_frames = int(lines[1].split("//")[1])
        return num_frames

    def get_xyz_info_for_all_files(self, folder, sorted_xyz_files):
        xyz_info_list = []
        for file_name in sorted_xyz_files:
            full_file_path = os.path.join(folder, file_name)
            num_frames = self.get_xyz_info(full_file_path)
            xyz_info_list.append(num_frames)
        return xyz_info_list

    def build_crystaldata(self, xyz_file_list):
        n = len(xyz_file_list)
        xyz_list = []
        self.statusBar().showMessage("Please wait, XYZ values are being extracted...")

        for i, xyz_file in enumerate(xyz_file_list):
            print(xyz_file)

            xyz, _, _ = CrystalShape.read_XYZ(xyz_file)

            print(xyz)
            self.xyz_list.append(xyz)
            print(len(self.xyz_list))
            self.progressBar.setValue(int(i / n) * 100)

        print(f"Number of Crystals Read: {len(xyz_list)}")