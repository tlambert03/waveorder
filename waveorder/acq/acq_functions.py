import glob
import json
import os
import time

import numpy as np
from iohub.mmstack import MMStack

try:
    from waveorder.io.mm_backend import MMBackend
except:
    pass


def generate_acq_settings(
    mm_backend: MMBackend,
    channel_group,
    channels=None,
    zstart=None,
    zend=None,
    zstep=None,
    save_dir=None,
    prefix=None,
    keep_shutter_open_channels=False,
    keep_shutter_open_slices=False,
):
    """
    This function generates acquisition settings for MDA sequences.
    It has default parameters for a multi-channels z-stack acquisition but does not yet
    support multi-position or multi-frame acquisitions.

    This also has default values for QLIPP Acquisition.  Can be used as a framework for other types
    of acquisitions

    Parameters
    ----------
    mm_backend:     (MMBackend) MM backend instance
    channel_group:  (str) name of the channel group 
    channels:       (list) list of channel names
    zstart:         (float) relative starting position for the z-stack
    zend:           (float) relative ending position for the z-stack
    zstep:          (float) step size for the z-stack
    save_dir:       (str) path to save directory
    prefix:         (str) name to save the data under
    keep_shutter_open_channels: (bool) keep shutter open between channels
    keep_shutter_open_slices:   (bool) keep shutter open between slices

    Returns
    -------
    settings:       (dict) acquisition settings dictionary
    """
    
    return mm_backend.generate_acquisition_settings(
        channel_group=channel_group,
        channels=channels,
        zstart=zstart,
        zend=zend,
        zstep=zstep,
        save_dir=save_dir,
        prefix=prefix,
        keep_shutter_open_channels=keep_shutter_open_channels,
        keep_shutter_open_slices=keep_shutter_open_slices,
    )


def acquire_from_settings(
    mm_backend: MMBackend,
    settings: dict,
    grab_images: bool = True,
) -> np.typing.NDArray:
    """Function to acquire an MDA acquisition with the MM backend.
    Assumes single position acquisition.

    Parameters
    ----------
    mm_backend : MMBackend
        MM backend instance
    settings : dict
        Acquisition settings dictionary
    grab_images : bool, optional
        return the acquired array, by default True

    Returns
    -------
    NDArray
        acquired images
    """
    mm_backend.run_acquisition(settings)

    time.sleep(3)

    # TODO: speed improvements in reading the data with direct acquisition?
    if grab_images:
        # get the most recent acquisition if multiple
        path = os.path.join(settings["root"], settings["prefix"])
        files = glob.glob(path + "*")
        index = max([int(x.split(path + "_")[1]) for x in files])
        return MMStack(path + f"_{index}")[0].xdata.to_numpy()
