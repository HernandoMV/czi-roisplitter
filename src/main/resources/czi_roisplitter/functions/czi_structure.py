# Hernando M. Vergara, SWC
# Feb 2021
# czi_structure.py
# functions to deal with .czi slide scanner files

#import sys
from loci.plugins.in import ImporterOptions
from loci.plugins import BF
from loci.common import Region


def get_data_structure(global_metadata):
    '''
    returns the number of images in a .czi file and the piramids of each
    '''
    # use the sizes of the images to know which images correspond to each slice
    Xsizes = []
    for i in range(len(global_metadata) - 2):
        Xsizes.append(global_metadata[i].sizeX)

    # keep counting as sizes decrease
    piramid_list = []
    counter = 0
    previous_size = float("inf")
    for s in Xsizes:
        if s < previous_size:
            # update
            counter += 1
            previous_size = s
        else:
            # append and reset
            piramid_list.append(counter)
            counter = 1
            previous_size = float("inf")
    # append last
    piramid_list.append(counter)

    return [len(piramid_list), piramid_list]


def get_binning_factor(max_indexes_list, num_of_piramids_list, global_metadata):
    '''
    for each image in the list get the maximum binarization value
    get also the binning factor (how much each pyramid step is binned)
    '''
    # use the sizes of the images to calculate the binning
    Xsizes = []
    for i in range(len(global_metadata) - 2):
        Xsizes.append(global_metadata[i].sizeX)

    bin_list = []
    step_list = []
    for i, maxind in enumerate(max_indexes_list):
        high_res = Xsizes[maxind]
        lowind = maxind + (num_of_piramids_list[i] - 1)
        low_res = Xsizes[lowind]
        # get the step (not a very smart way)
        step = Xsizes[maxind] / Xsizes[maxind + 1]

        bin_list.append(high_res / low_res)
        step_list.append(step)

    return bin_list, step_list


def get_maxres_indexes(piramid_list):
    # the first image is high res
    mr_list = [0]
    for i in range(len(piramid_list) - 1):
        mr_list.append(piramid_list[i] + mr_list[i])

    return mr_list


def open_czi_series(file_name, series_number, rect=False):
    # see https://downloads.openmicroscopy.org/bio-formats/5.5.1/api/loci/plugins/in/ImporterOptions.html
    options = ImporterOptions()
    options.setId(file_name)
    options.setColorMode(ImporterOptions.COLOR_MODE_GRAYSCALE)
    # select image to open
    options.setOpenAllSeries(False)
    options.setAutoscale(False)
    options.setSeriesOn(series_number, True)
    # default is not to crop
    options.setCrop(False)
    if rect:  # crop if asked for
        options.setCrop(True)
        options.setCropRegion(series_number, Region(rect[0], rect[1], rect[2], rect[3]))
    imps = BF.openImagePlus(options)

    return imps[0]
