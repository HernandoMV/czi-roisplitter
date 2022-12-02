# Hernando M. Vergara, SWC
# Feb 2021
# image_manipulation.py
# generic functions

from ij import IJ, ImagePlus, ImageStack
from ij.plugin.frame import RoiManager
from ij.process import FloatProcessor, ImageConverter
from ij.plugin import ImageCalculator, Duplicator
from ij.plugin.filter import GaussianBlur
from ij.gui import Roi, PolygonRoi


def extractChannel(imp, nChannel, nFrame):
    """Extract a stack for a specific color channel and time frame"""
    stack = imp.getImageStack()
    ch = ImageStack(imp.width, imp.height)
    for i in range(1, imp.getNSlices() + 1):
        index = imp.getStackIndex(nChannel, i, nFrame)
        ch.addSlice(str(i), stack.getProcessor(index))
    stack_to_return = ImagePlus("Channel " + str(nChannel), ch)
    stack_to_return.copyScale(imp)
    return stack_to_return


def create_mask_from_roi(reg_roi, region_name, image):
    # create new image
    fp = FloatProcessor(image.getWidth(), image.getHeight())
    imp = ImagePlus(region_name, fp)
    # draw it
    fp.setRoi(reg_roi)
    fp.fill(reg_roi.getMask())
    ImageConverter(imp).convertToGray16()
    imp.setTitle(region_name)
    return imp


def apply_mask_to_image(targetImage, maskImage, title, blurval):
    mask = maskImage.getProcessor()
    # target = targetImage.getProcessor()
    masked_image = Duplicator().run(targetImage)
    masked_image.setTitle(title)
    mask.invert()
    masked_image = ImageCalculator().run(masked_image, maskImage, "subtract")
    # blur
    GaussianBlur().blurGaussian(masked_image.getProcessor(), blurval)
    return masked_image


def find_threshold(image_title, method):
    IJ.selectWindow(image_title)
    im = IJ.getImage()
    imp = im.getProcessor()
    imp.setAutoThreshold(method + " dark")
    lower = imp.getMinThreshold()
    upper = max(imp.getPixels())
    return lower, upper


def ARAcoords_of_point(point, coords, atlas_resolution):
    # order is ap, dv, ml
    reg_coords = []
    for i in range(1, 4):
        coords.setSlice(i)
        ip = coords.getProcessor()
        coord = ip.getPixelValue(point[0], point[1])
        # Convert to pixel coordinates and append
        sc_c = int(coord * 1000 / atlas_resolution)

        reg_coords.append(sc_c)

    return reg_coords[0], reg_coords[1], reg_coords[2]


def paint_reg_roi(registered_roi, sample_im, mask_name):
    # create new
    imp = IJ.createImage(
        "roi_mask_" + mask_name,
        "8-bit black",
        sample_im.getWidth(),
        sample_im.getHeight(),
        1,
    )
    ip = imp.getProcessor()
    # paint pixels
    for pixel in registered_roi:
        ip.set(pixel[0], pixel[1], 255)
    # erode and dilate to clean
    IJ.run(imp, "Erode", "")
    IJ.run(imp, "Dilate", "")

    return imp


def image_to_roi(image):
    xs = []
    ys = []
    imp = image.getProcessor()
    for x in range(imp.getWidth()):
        for y in range(imp.getHeight()):
            if imp.getPixel(x, y) == 255:
                xs.append(x)
                ys.append(y)

    roi = PolygonRoi(xs, ys, len(xs), Roi.POLYGON)
    return roi


def roi_from_mask(mask, coords_im, mask_name):
    # paint the points in a new image to see how well reconstituted it is
    imp = paint_reg_roi(mask, coords_im, mask_name)
    imp.show()
    imp_tit = imp.getTitle()
    rm = RoiManager()
    IJ.selectWindow(imp_tit)
    mask = IJ.getImage()
    IJ.setThreshold(mask, 1, 255)
    IJ.run(mask, "Create Selection", "")
    IJ.selectWindow(imp_tit)
    rm.runCommand("add")
    IJ.selectWindow(imp_tit)
    IJ.run("Close")
    roi = rm.getRoi(0)
    rm.close()

    return roi


def paint_atlas(imp, roi, slice_num):
    ip = imp.getProcessor()
    pixels = roi.getContainedPoints()
    for point in pixels:
        imp.setSlice(slice_num)
        ip.set(point.x, point.y, 255)


def save_interpolated(im, name):
    imtit = im.getTitle()
    IJ.selectWindow(imtit)
    IJ.run("3D Binary Interpolate", "make")
    IJ.selectWindow("interpolated")
    imint = IJ.getImage()
    IJ.saveAsTiff(imint, name)
    imint.close()
    imint.flush()
