# Hernando M. Vergara
# March 2020. Coronavirus quarantine :)
# CZI_SlideScanner_ROIsubdivider.py takes as input a .czi file from the slide scanner
# The input files should contain
# ...
# It subdivides the drawn ROIs into square rois within that ROI, and saves them independently

# This is optimized for working with the low and high resolution images generated when acquiring
# with the 40x objective


from loci.plugins.in import ImporterOptions
from loci.formats import ImageReader
from javax.swing import JFrame, JButton, JTextField, JCheckBox, JList, \
    JScrollPane, DefaultListModel
from java.awt import GridLayout, Dimension, Label
from ij.io import RoiEncoder
from ij import IJ
from ij.plugin import ContrastEnhancer
from os import listdir, path, mkdir, makedirs
from ij.gui import Overlay
import sys
sys.path.append(path.abspath(path.dirname(__file__)))
from functions.czi_structure import get_data_structure, get_binning_factor, open_czi_series, \
    get_maxres_indexes
from functions.image_manipulation import extractChannel
from functions.text_manipulation import get_core_names, get_registered_slices_folder, \
    get_registered_regions_path
from functions.roi_and_ov_manipulation import get_corners, overlay_corners, overlay_roi, \
    clean_corners, write_roi_numbers, get_region_from_file

class gui(JFrame):
    def __init__(self):  # constructor
        # origing of coordinates
        self.coordx = 10
        self.coordy = 10

        # inintialize values
        self.Canvas = None
        self.default_naming = 'MouseID_ExperimentalGroup_slide-X'

        # create panel (what is inside the GUI)
        self.panel = self.getContentPane()
        self.panel.setLayout(GridLayout(10, 2))
        self.setTitle('Subdividing ROIs')

        # define buttons here:
        self.subimage_number = DefaultListModel()
        mylist = JList(self.subimage_number, valueChanged=self.open_lowres_image)
        # mylist.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
        mylist.setLayoutOrientation(JList.VERTICAL)
        mylist.setVisibleRowCount(1)
        listScroller1 = JScrollPane(mylist)
        listScroller1.setPreferredSize(Dimension(300, 90))

        quitButton = JButton("Quit", actionPerformed=self.quit)
        selectInputFolderButton = JButton("Select Input", actionPerformed=self.select_input)
        cubifyROIButton = JButton("Cubify ROI", actionPerformed=self.cubify_ROI)
        saveButton = JButton("Save ROIs", actionPerformed=self.save_ROIs)

        self.textfield1 = JTextField('6')
        self.textfield2 = JTextField(self.default_naming)
        self.textfield3 = JTextField('R-Tail')
        # self.textfield4 = JTextField('6, 4, 22.619')
        self.textfield4 = JTextField('')
        self.textfield5 = JTextField('0')

        # load ARA regions buttons
        loadARARegionButton = JButton("Load ARA region", actionPerformed=self.load_ARA_region)
        self.textfield_ARA_region = JTextField('Both-Caudoputamen')

        # create a button to remove ROIs
        removeROIsButton = JButton("Select ROI numbers to remove", actionPerformed=self.remove_corners)
        self.textfield_remove_ROIs = JTextField('')

        # add buttons here
        self.panel.add(Label("Name your image, or use filename"))
        self.panel.add(self.textfield2)
        self.panel.add(selectInputFolderButton)
        self.panel.add(listScroller1)
        self.panel.add(loadARARegionButton)
        self.panel.add(self.textfield_ARA_region)
        self.panel.add(Label("Adjust the size of the squared ROIs"))
        self.panel.add(self.textfield1)
        self.panel.add(Label("give a name of your hand-drawn ROI"))
        self.panel.add(self.textfield3)
        self.panel.add(Label("For ARA: piram, ch, res"))
        # piramid number (high to low), channel number, final resolution (um/px)"))
        self.panel.add(self.textfield4)
        self.panel.add(Label("Piramid to check (0:none; 1:highest)"))
        self.panel.add(self.textfield5)
        self.panel.add(removeROIsButton)
        self.panel.add(self.textfield_remove_ROIs)
        self.panel.add(cubifyROIButton)
        self.panel.add(saveButton)
        self.panel.add(quitButton)

        # other stuff to improve the look
        self.pack()  # packs the frame
        self.setVisible(True)  # shows the JFrame
        self.setLocation(self.coordx, self.coordy)

    # define functions for the buttons:
    def quit(self, event):  # quit the gui
        self.dispose()
        IJ.run("Close All")

    def select_input(self, event):
        # get the info about the number of images in the file
        self.input_path = IJ.getFilePath("Choose a File")
        # if default naming is not changed use file name
        if self.textfield2.text == self.default_naming:
            self.file_core_name = path.basename(self.input_path).split('.czi')[0]
        else:
            self.file_core_name = self.textfield2.text
        # put that name in the text field
        self.panel.getComponents()[1].setText(self.file_core_name)

        reader = ImageReader()
        reader.setId(self.input_path)
        metadata_list = reader.getCoreMetadataList()
        # slide scanner makes a piramid of X for every ROI you draw
        # resolution is not updated in the metadata so it needs to be calculated manually
        number_of_images, self.num_of_piramids_list = get_data_structure(metadata_list)
        print("Number of images is " + str(number_of_images))
        # get the indexes of the maximum resolution images
        self.max_res_indexes = get_maxres_indexes(self.num_of_piramids_list)
        print("Number of pyramids are " + str(self.num_of_piramids_list))
        # set names of subimages in the list, waiting to compare to current outputs
        self.possible_slices = [self.file_core_name + "_slice-" + str(n)
                                for n in range(number_of_images)]

        self.binFactor_list, self.binStep_list = get_binning_factor(self.max_res_indexes,
                                                self.num_of_piramids_list, metadata_list)
        print("Binning factors are " + str(self.binFactor_list))
        print("Binning steps are " + str(self.binStep_list))

        # create output directory if it doesn't exist
        # get the animal id
        animal_id = self.file_core_name.split('_')[0]
        self.output_path = path.join(path.dirname(path.dirname(self.input_path)),
                                     "Processed_data", animal_id, "ROIs")
        if path.isdir(self.output_path):
            print("Output path was already created")
        else:
            makedirs(self.output_path)
            print("Output path created")

        # update_lists depending on whether something has been processed already
        self.update_list()

    def update_list(self):
        # remove stuff from lists:
        # TODO
        # populate the list
        for f in set(self.possible_slices):
            self.subimage_number.addElement(f)

    def open_lowres_image(self, e):
        sender = e.getSource()
        IJ.run("Close All")
        if not e.getValueIsAdjusting():
            self.name = sender.getSelectedValue()
            print(self.name)
            # parse the slice number
            self.sl_num = int(self.name.split('-')[-1])
            print("Opening slice " + str(self.sl_num))

            if not path.exists(self.input_path):
                print("I don't find the file, which is weird as I just found it before")
            else:
                # get the number of piramids for that image, the index of highres and the binning
                self.num_of_piramids = self.num_of_piramids_list[self.sl_num]
                self.high_res_index = self.max_res_indexes[self.sl_num]
                # get Xth lowest resolution binned, depending on the number
                # of resolutions. The order is higher to lower.
                # This number is hard-coded for now
                LOW_RES_TO_OPEN = 2
                series_num = self.high_res_index + self.num_of_piramids - LOW_RES_TO_OPEN
                self.binStep = self.binStep_list[self.sl_num]
                self.binFactor = self.binFactor_list[self.sl_num] / (self.binStep ** (LOW_RES_TO_OPEN - 1))
                self.low_res_image = open_czi_series(self.input_path, series_num)  # read the image
                # save the resolution (every image has the high-resolution information)
                self.res_xy_size = self.low_res_image.getCalibration().pixelWidth
                self.res_units = self.low_res_image.getCalibration().getXUnit()
                # play with that one, and do the real processing in the background
                # select the DAPI channel and adjust the intensity
                self.lr_dapi = extractChannel(self.low_res_image, 1, 1)
                ContrastEnhancer().stretchHistogram(self.lr_dapi, 0.35)
                self.lr_dapi.setTitle(self.name)
                self.lr_dapi.show()
                # reposition image
                self.lr_dapi.getWindow().setLocation(620, 10)
                self.lr_dapi.updateAndDraw()

                # clean
                self.low_res_image.close()
                self.low_res_image.flush()

    def load_ARA_region(self, e):
        # look for the folder and avoid conflicts
        registration_folder = path.join(path.dirname(self.output_path), 'Registration/')
        regions_folder, registration_resolution = get_registered_slices_folder(registration_folder)
        # check the resolution to adjust roi later
        res_of_lr_dapi = self.res_xy_size * self.binFactor
        regions_transform_factor = registration_resolution / res_of_lr_dapi
        # check that there is a zip file with the rois for this slice
        regions_path = get_registered_regions_path(regions_folder, self.name)

        # get the roi from the region
        # get the name of the region (assumes that L/R is written as well)
        region_name = self.textfield_ARA_region.text.split('-')[1]
        self.roi = get_region_from_file(input_file=regions_path,
                                        region_name=region_name,
                                        image=self.lr_dapi,
                                        scale_factor=regions_transform_factor)

        # show it
        #self.lr_dapi.getProcessor().setRoi(self.roi)
        self.ov = Overlay()
        self.ov = overlay_roi(self.roi, self.ov)
        self.lr_dapi.setOverlay(self.ov)
        self.lr_dapi.updateAndDraw()
        #rm_regions.selectAndMakeVisible(self.lr_dapi, region_index)

    
    def cubify_ROI(self, e):
        # check if this was selected from ARA regions and change naming
        if not hasattr(self, 'roi'):
            self.manualROI_name = self.name + "_manualROI-" + self.textfield3.text
        else:
            self.manualROI_name = self.name + "_manualROI-" + self.textfield_ARA_region.text

        # warn the user if that ROI exists already in the processed data
        self.processed_files = listdir(self.output_path)
        self.out_core_names = get_core_names(self.processed_files, self.file_core_name)
        if self.manualROI_name in self.out_core_names:
            print("##################                       ##################")
            print("CAREFUL!!!! This ROI already exists in your processed data:")
            print("##################                       ##################")

        print(self.manualROI_name)

        # set square roi size in the low resolution level
        gui_adjust = 128  # for historic reasons
        hr_L = int(self.textfield1.text) * gui_adjust
        # convert back to low resolution
        self.L = hr_L / self.binFactor
        # get info
        tit = self.lr_dapi.getTitle()
        if not hasattr(self, 'roi'):
            self.roi = self.lr_dapi.getRoi()

        # get corners
        corners = get_corners(self.roi, self.L)
        # self.corners_cleaned = clean_corners(corners, self.roi, self.L)
        self.corners_cleaned = corners
        # get the overlay
        self.ov = overlay_corners(self.corners_cleaned, self.L)
        self.ov = overlay_roi(self.roi, self.ov)
        # write roi name
        self.ov = write_roi_numbers(self.ov, self.corners_cleaned, self.L)
        # overlay
        self.lr_dapi.setOverlay(self.ov)
        self.lr_dapi.updateAndDraw()

        # open the Xth highest resolution one to see if it is in focus
        if int(self.textfield5.text) != 0:
            pir_for_focus = int(self.textfield5.text)
            bf_corr = self.binFactor / (self.binStep ** (pir_for_focus - 1))
            min_x = int(min([x[0] for x in self.corners_cleaned]) * bf_corr)
            min_y = int(min([x[1] for x in self.corners_cleaned]) * bf_corr)
            max_x = int((max([x[0] for x in self.corners_cleaned]) + self.L) * bf_corr)
            max_y = int((max([x[1] for x in self.corners_cleaned]) + self.L) * bf_corr)
            series_num = self.high_res_index + pir_for_focus - 1
            self.med_res_image = open_czi_series(
                self.input_path, series_num,
                rect=[min_x, min_y, max_x - min_x, max_y - min_y])  # read the image
            # play with that one, and do the real processing in the background
            self.med_res_image.show()
            self.med_res_image.setDisplayMode(IJ.COMPOSITE)
            color_order = ['Grays', 'Green', 'Red', 'Cyan']
            for c in range(self.med_res_image.getNChannels()):
                self.med_res_image.setC(c + 1)
                IJ.run(color_order[c])
                ContrastEnhancer().stretchHistogram(self.med_res_image, 0.35)
                self.med_res_image.updateAndDraw()
            # rename
            self.med_res_image.setTitle(self.manualROI_name)
            # I don't know what comp is....
            #comp = CompositeImage(self.low_res_image, CompositeImage.COLOR)
            #comp.show()
            #IJ.Stack.setDisplayMode("composite")
            # IJ.run("RGB")

    def remove_corners(self, e):
        # parse the input
        # separated numbers by commas
        if ',' in self.textfield_remove_ROIs.text:
            rois_to_remove = [int(i) for i in self.textfield_remove_ROIs.text.split(',')]
        
        # a range
        elif '-' in self.textfield_remove_ROIs.text:
            range_nums = [int(i) for i in self.textfield_remove_ROIs.text.split('-')]
            rois_to_remove = range(range_nums[0], range_nums[1] + 1)

        # a single number
        else:
            try:
                rois_to_remove = [int(self.textfield_remove_ROIs.text)]

            except ValueError:
                print('Cannot interpret your input, use commas or a dash for a range')
                return

        print('Removing ROIs: {}'.format(rois_to_remove))

        for roi in sorted(rois_to_remove, reverse=True):
            self.corners_cleaned.pop(roi - 1)

        # get the overlay
        self.ov = overlay_corners(self.corners_cleaned, self.L)
        self.ov = overlay_roi(self.roi, self.ov)
        # write roi name
        self.ov = write_roi_numbers(self.ov, self.corners_cleaned, self.L)
        # overlay
        self.lr_dapi.setOverlay(self.ov)
        self.lr_dapi.updateAndDraw()




        # # get the overlay
        # self.ov = overlay_corners(self.corners_cleaned, self.L)
        # self.ov = overlay_roi(self.roi, self.ov)
        # # write roi name
        # self.ov = write_roi_numbers(self.ov, self.corners_cleaned, self.L)
        # # overlay
        # self.lr_dapi.setOverlay(self.ov)
        # self.lr_dapi.updateAndDraw()

    def save_ROIs(self, e):
        # save the low resolution image for registration
        self.save_registration_image()

        print('Saving ROIs')
        # add a counter for the ROI name
        roiID = 1

        # create a file to save the ROI coordinates
        # create output directory if it doesn't exist
        self.roi_output_path = path.join(self.output_path, "000_ManualROIs_info")
        if path.isdir(self.roi_output_path):
            print("Output path for ROIs information was already created")
        else:
            mkdir(self.roi_output_path)
            print("Output path for ROIs created")
        roi_points_file_path = path.join(self.roi_output_path, self.manualROI_name +
                                         "_roi_positions.txt")
        with open(roi_points_file_path, "w") as roi_points_file:
            roi_points_file.write("{}, {}, {}, {}, {}, {}".
                                  format("roiID", "high_res_x_pos",
                                         "high_res_y_pos", "registration_image_pixel_size",
                                         "high_res_pixel_size", "units"))

        # for each roi
        for [x, y] in self.corners_cleaned:
            print('   -> processing square ROI number ' + str(roiID))
            # tranlate coordinates to high resolution
            xt = int(x * self.binFactor)
            yt = int(y * self.binFactor)
            Lt = int(self.L * self.binFactor)
            # save the corner coordinates of the ROI in a file
            with open(roi_points_file_path, "a") as roi_points_file:
                roi_points_file.write("\n{}, {}, {}, {}, {}, {}".
                                      format(roiID, xt, yt, self.reg_final_res,
                                             self.res_xy_size, self.res_units))

            # open the high resolution image on that roi
            series_num = self.high_res_index
            hr_imp = open_czi_series(self.input_path, series_num, rect=[xt, yt, Lt, Lt])
            # hr_imp.show()
            # name of this ROI
            Roi_name = self.manualROI_name + "_squareROI-" + str(roiID)
            # for each of the channels
            for c in range(1, (hr_imp.getNChannels() + 1)):
                # get the channel
                channel = extractChannel(hr_imp, c, 1)
                # save with coherent name
                IJ.saveAsTiff(channel, path.join(self.output_path, Roi_name + "_channel-" + str(c)))
                # close and flush memory
                channel.close()
                channel.flush()
            # increase counter
            roiID += 1
            # close and flush memory
            hr_imp.close()
            hr_imp.flush()
        print('ROIs saved, saving summary figure')

        # save summary
        # create output directory if it doesn't exist
        self.summary_output_path = path.join(self.output_path, "000_Summary_of_ROIs")
        if path.isdir(self.summary_output_path):
            print("Output path for summary was already created")
        else:
            mkdir(self.summary_output_path)
            print("Output path for summary created")
        IJ.selectWindow(self.name)
        IJ.run("Flatten")
        imp = IJ.getImage()
        IJ.saveAsTiff(imp, path.join(
            self.summary_output_path,
            self.manualROI_name + "_summaryImage"))
        print("summary image saved")
        IJ.run("Close All")

        # save manual ROI
        RoiEncoder.save(self.roi, path.join(self.roi_output_path, self.manualROI_name))
        print("roi information saved, closing images and finishing")
        IJ.run("Close All")

    def save_registration_image(self):
        # make this conditional to the text
        if self.textfield4.text == '':
            self.reg_final_res = 0
            return
        reg_text_info = self.textfield4.text.split(',')
        reg_pir_num = int(reg_text_info[0])
        reg_channel = int(reg_text_info[1])
        self.reg_final_res = float(reg_text_info[2])

        output_res_path = 'Slices_for_ARA_registration_channel-' + str(reg_channel) + '_' + str(self.reg_final_res) + '-umpx'
        self.forreg_output_path = path.join(path.dirname(self.output_path), 'Registration', output_res_path)

        if path.isdir(self.forreg_output_path):
            print("Output path for low resolution slices was already created")
        else:
            mkdir(self.forreg_output_path)
            print("Output path for low resolution slices created")

        # check that this slice has not been saved before
        reg_slice_name = path.join(self.forreg_output_path, self.name)
        if path.isfile(reg_slice_name + '.tif'):
            print("Registration slice already exists")
        else:
            # save otherwise
            print("Saving for registration channel {} at {} um/px".format(reg_channel, self.reg_final_res))
            # get the Xth resolution image and Xth channel for saving it for registration
            series_num = self.high_res_index + reg_pir_num
            self.raw_reg_image = open_czi_series(self.input_path, series_num)  # read the image
            self.regist_image = extractChannel(self.raw_reg_image, reg_channel, 1)
            ContrastEnhancer().stretchHistogram(self.regist_image, 0.35)
            # self.regist_image.show()

            self.regist_image.getProcessor().resetRoi()
            # reset min and max automatically
            # convert to 8-bit (which also applies the contrast)
            # ImageConverter(self.regist_image).convertToGray8()
            # convert to Xum/px so that it can be aligned to ARA
            reg_im_bin_factor = self.binStep ** reg_pir_num
            regres_resolution = reg_im_bin_factor * self.res_xy_size
            rescale_factor = regres_resolution / self.reg_final_res
            new_width = int(rescale_factor * self.regist_image.getWidth())
            # self.lr_dapi_reg.getProcessor().scale(rescale_factor, rescale_factor)
            ip = self.regist_image.getProcessor().resize(new_width)
            self.regist_image.setProcessor(ip)
            # Add the information to the metadata
            self.regist_image.getCalibration().pixelWidth = self.reg_final_res
            self.regist_image.getCalibration().pixelHeight = self.reg_final_res
            self.regist_image.getCalibration().pixelDepth = 1
            self.regist_image.getCalibration().setXUnit("micrometer")
            self.regist_image.getCalibration().setYUnit("micrometer")
            self.regist_image.getCalibration().setZUnit("micrometer")
            # self.lr_dapi_reg.getProcessor().resetRoi()
            IJ.saveAsTiff(self.regist_image, reg_slice_name)
            self.regist_image.close()
            self.regist_image.flush()
            print("Slice for registration saved")


if __name__ in ['__builtin__', '__main__']:
    gui()
