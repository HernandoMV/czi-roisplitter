# Hernando M. Vergara, SWC
# Feb 2021
# text_manipulation.py
# generic functions

from os import listdir, path


def get_core_names(file_names, core_name):
    out_names = []
    for name in file_names:
        if core_name in name:
            # parse for the Slices
            name_pieces = name.split("_")
            mr_index_array = [
                i for i, s in enumerate(name_pieces) if "manualROI-" in s
            ]
            # check that there is only one occurrence
            if len(mr_index_array) == 1:
                out_names.append(
                    "_".join(name_pieces[0 : (mr_index_array[0] + 1)])
                )
            else:
                raise NameError("Your file name should not contain slice-")
    return set(out_names)


def get_registered_slices_folder(reg_folder):
    """
    Finds the folder where the slices are and returns it together with the resolution
    of the registered slices
    """
    # get the filelist
    list_in_dir = listdir(reg_folder)
    # get those folders that match the pattern
    potential_folders = [
        i for i in list_in_dir if i.startswith("Slices_for_ARA_registration")
    ]
    # make sure there is only one
    if len(potential_folders) > 1:
        print(
            "More than one potential registration folder, please correct!!!!"
        )
    else:
        reg_sl_folder = potential_folders[0]
    # get the registration resolution
    registration_resolution = get_resolution_from_folder_name(reg_sl_folder)
    regions_full_path = path.join(reg_folder, reg_sl_folder)

    return regions_full_path, registration_resolution


def get_resolution_from_folder_name(reg_sl_folder):
    folder_last_piece = reg_sl_folder.split("_")[-1]
    res = folder_last_piece.split("-")[0]

    return float(res)


def get_registered_regions_path(regions_folder, slice_name):
    regions_file_name = path.join(regions_folder, slice_name + ".tif_ch0.zip")
    if not path.isfile(regions_file_name):
        print("Slice not registered or regions not saved!!!!!!")
    return regions_file_name


def get_lesion_coord_file(
    full_file_path, file_end, coords_file_ending, reg_path
):
    f_name = path.basename(full_file_path)
    slice_name = f_name.split(file_end)[0] + ".tif"
    cf_name = slice_name + coords_file_ending
    coords_file = reg_path + cf_name

    return coords_file
