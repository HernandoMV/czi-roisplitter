# Hernando M. Vergara, SWC
# Feb 2021
# roi_and_ov_manipulation.py
# generic functions to manipulate ROIs and overlays

from ij.gui import Roi, TextRoi, PolygonRoi, Overlay
from java.awt import Color, Font
from ij.plugin.frame import RoiManager
from ij.process import FloatProcessor, ImageConverter
from ij import ImagePlus, IJ
from os import path
import sys

sys.path.append(path.abspath(path.dirname(__file__)))
from czi_rs_functions.image_manipulation import ARAcoords_of_point


def get_corners(roi, L):
    # get the points inside roi
    poly = roi.getContainedFloatPoints()
    xs = poly.xpoints
    ys = poly.ypoints
    # create an empty set to hold the corners
    corners = set()
    for x, y in zip(xs, ys):
        # add the modulo of the size to set
        # need to be tuple, lists can't be added to a set
        xc = x - x % L
        yc = y - y % L
        corners.add((xc, yc))

    # sort rois first by x and then by y coordinates
    corners = sorted(sorted(corners, key=lambda item: item[1]))
    # remove the one in the top corner
    corners.pop(0)

    return corners


def overlay_corners(corners, L):
    ov = Overlay()
    for [x, y] in corners:
        rect = Roi(x, y, L, L)
        rect.setStrokeColor(Color.RED)
        rect.setLineWidth(2)
        ov.add(rect)
    return ov


def overlay_roi(roi, ov):
    roi.setStrokeColor(Color.GREEN)
    roi.setLineWidth(4)
    ov.add(roi)
    return ov


def clean_corners(corners, roi, L):
    # get the points inside roi
    poly = roi.getContainedPoints()
    xs = [int(p.getX()) for p in poly]
    ys = [int(p.getY()) for p in poly]
    points = zip(xs, ys)
    corners_cleaned = set()
    for c in corners:
        if c in points:  # if the corner is inside
            if (
                c[0] + L,
                c[1] + L,
            ) in points:  # if the opposite corner is inside
                if (c[0] + L, c[1]) in points:
                    if (c[0], c[1] + L) in points:
                        corners_cleaned.add(c)
    # sort rois first by x and then by y coordinates
    return sorted(sorted(corners_cleaned, key=lambda item: item[1]))


def write_roi_numbers(ov, corners, L):
    fontsize = int(L / 1.5)
    roiID = 1
    for [x, y] in corners:
        text = TextRoi(
            x, y, L, L, str(roiID), Font("Arial", Font.BOLD, fontsize)
        )
        text.setJustification(2)
        text.setColor(Color.RED)
        ov.add(text)
        roiID += 1
    return ov


def get_region_from_file(input_file, region_name, image, scale_factor):
    # load the roi manager
    rm_regions = RoiManager()
    # load the regions file
    rm_regions.runCommand("Open", input_file)
    # get a list of the names
    regions_number = rm_regions.getCount()
    region_names = []
    for i in range(regions_number):
        region_names.append(rm_regions.getName(i))
    # check that there is a roi with that name
    region_index = region_names.index(region_name)
    reg_roi = rm_regions.getRoi(region_index)
    # transform to the proper resolution
    roi_polygon = reg_roi.getPolygon()
    xs = [round(i * scale_factor) for i in roi_polygon.xpoints]
    ys = [round(i * scale_factor) for i in roi_polygon.ypoints]
    roi = PolygonRoi(xs, ys, len(xs), Roi.POLYGON)

    # clean it
    # create new image
    fp = FloatProcessor(image.getWidth(), image.getHeight())
    imp = ImagePlus("mask", fp)
    # draw it
    fp.setRoi(roi)
    fp.fill(roi.getMask())
    # erode and dilate
    ImageConverter(imp).convertToGray8()
    fp = imp.getProcessor()
    fp.invert()
    fp.erode()
    fp.erode()
    fp.dilate()
    fp.dilate()
    imp.show()
    # get new roi from it
    IJ.run("Create Selection")
    roi = imp.getRoi()
    imp.close()
    imp.flush()

    # close roi manager
    rm_regions.close()

    return roi


def get_ARA_roi(input_file, region_name):
    # load the roi manager
    rm_regions = RoiManager()
    # load the regions file
    rm_regions.runCommand("Open", input_file)
    # get a list of the names
    regions_number = rm_regions.getCount()
    region_names = []
    for i in range(regions_number):
        region_names.append(rm_regions.getName(i))
    # check that there is a roi with that name
    region_index = region_names.index(region_name)
    reg_roi = rm_regions.getRoi(region_index)
    # close roi manager
    rm_regions.close()
    return reg_roi


def roi_to_ARA(roi, coords, atlas_resolution=25.0, ap_offset=0.0):
    # get ROI xy coordinates
    # roi_polygon = roi.getPolygon()
    # xs = roi_polygon.xpoints
    # ys = roi_polygon.ypoints
    # point_list = zip(xs,ys)
    point_list = roi.getContainedPoints()
    # find the ARA xyz coordinates
    xt = []
    yt = []
    zt = []
    for point in point_list:
        point_a = [point.x, point.y]
        z, y, x = ARAcoords_of_point(point_a, coords, atlas_resolution)
        # append
        xt.append(x)
        yt.append(y)
        zt.append(z)

    # get the points
    reg_filling = list(zip(xt, yt))

    # adjust offset
    ozt = [int(ap_offset * 1000 / atlas_resolution) + z for z in zt]

    # start with z as the mean
    mean_z = int(sum(ozt) / len(ozt))

    return reg_filling, mean_z, ozt
