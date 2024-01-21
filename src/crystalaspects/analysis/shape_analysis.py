import logging
import re
import sys
from collections import namedtuple
from pathlib import Path

import numpy as np
import pandas as pd
import trimesh
from scipy.spatial import ConvexHull

logger = logging.getLogger("CA:ShapeAnalysis")


class CrystalShape:
    def __init__(
        self,
    ):
        self.xyz = None
        self.shape_tuple = namedtuple(
            "shape_info",
            "x, y, z, pc1, pc2, pc3, aspect1, aspect2, sa, vol, sa_vol, shape",
        )

    def set_xyz(self, xyz_array=None, filepath=None):
        xyz_vals = None
        # Check if the xyz_array is provided and is not None
        if xyz_array is not None:
            xyz_vals = np.array(xyz_array)

        # If a filepath is provided, read the XYZ from the file
        if filepath:
            xyz_vals, _, _ = self.read_XYZ(filepath=filepath)

        # Error handling for no valid input
        if xyz_vals is None:
            raise ValueError("Provide XYZ as either an array or a filepath.")

        if xyz_vals.shape[1] == 3:
            xyz_vals = xyz_vals
        if xyz_vals.shape[1] > 3:
            xyz_vals = xyz_vals[0:, 3:6]

        self.xyz = xyz_vals

    def _normalise_verts(self, verts):
        """Normalises xyz crystal shape output through a
        transformation to unit lenghts and centering."""

        centered = verts - np.mean(verts, axis=0)
        norm = np.linalg.norm(centered, axis=1).max()
        centered /= norm

        return centered

    @staticmethod
    def read_XYZ(filepath, progress=True):
        """Read in shape data and generates a np arrary.
        Supported formats:
            .XYZ
            .txt (.xyz format)
            .stl
        """
        filepath = Path(filepath)
        logger.debug(filepath)
        xyz_movie = {}

        try:
            if filepath.suffix == ".XYZ":
                logger.debug("XYZ: File read!")
                xyz = np.loadtxt(filepath, skiprows=2)
            if filepath.suffix == ".txt":
                logger.debug("xyz: File read!")
                xyz = np.loadtxt(filepath, skiprows=2)
            if filepath.suffix == ".stl":
                logger.debug("stl: File read!")
                xyz = trimesh.load(filepath)

            progress_num = 100

        except ValueError:
            # Set to warning currently since behavious was not tested
            # TO DO: Test and lower logging level
            logger.warning("Looking for Video")
            with open(filepath, "r", encoding="utf-8") as file:
                lines = file.readlines()
                num_frames = int(lines[1].split("//")[1])
                logger.info("Number of Frames: %s", num_frames)

            particle_num_line = 0
            frame_line = 2
            for frame in range(num_frames):
                num_particles = int(lines[particle_num_line])
                xyz = np.loadtxt(lines[frame_line : (frame_line + num_particles)])
                xyz_movie[frame] = xyz
                particle_num_line = frame_line + num_particles
                frame_line = particle_num_line + 2

                progress_num = ((frame + 1) / num_frames) * 100
                # print(
                #     f"#####\nFRAME NUMBER: {frame}\n"
                #     f"Particle Number Line: {particle_num_line}\n"
                #     f"Frame Start Line: {frame_line}\n"
                #     f"Frame End Line: {frame_line + num_particles}\n"
                #     f"Number of Particles read: {frame_line}\n",
                #     f"Number of Particles in list: {xyz.shape[0]}\n",
                #     end="\r",
                # )

        return (xyz, xyz_movie, progress_num)

    def get_sa_vol_ratio(self):
        """Returns 3D data of a crystal shape,
        Volume:
        Surface Area:
        SA:Vol."""
        hull = ConvexHull(self.xyz)
        vol_hull = hull.volume
        sa_hull = hull.area
        sa_vol = sa_hull / vol_hull

        sa_vol_ratio_array = np.array([sa_hull, vol_hull, sa_vol])

        return sa_vol_ratio_array

    def get_shape_class(self, aspect1, aspect2):
        """Determining the crystal shape
        based on the aspect ratios.
        """

        threshold = 2 / 3

        aspects = (aspect1 > threshold, aspect2 > threshold)

        shapes = {
            (False, False): "Lath",
            (False, True): "Plate",
            (True, True): "Block",
            (True, False): "Needle",
        }

        return shapes.get(aspects, "unknown")

    def get_zingg_analysis(self, get_sa_vol=True):
        """
        Crystal is aligned in so that the
        first principal component is aligned
        with the cartesian x asis -
        thus allowing for zingg aspect ratio analysis
        using a bounding box.
        """
        # Perform PCA to find the principal components
        u, s, vh = np.linalg.svd(self.xyz, full_matrices=False)
        # Align the principal component with the x-axis
        transformed_xyz = self.xyz @ vh.T
        # Get the explained variance
        sorted_pca = np.sort(s**2 / self.xyz.shape[0])

        # Calculate min, max, and lengths for x, y, z coordinates
        # based on the transformed (rotated) coordinates
        mins = np.min(transformed_xyz, axis=0)
        maxs = np.max(transformed_xyz, axis=0)
        lengths = maxs - mins

        # Calculate aspect ratios
        sorted_lengths = np.sort(lengths)
        aspect1 = sorted_lengths[0] / sorted_lengths[1] if sorted_lengths[1] != 0 else 0
        aspect2 = sorted_lengths[1] / sorted_lengths[2] if sorted_lengths[2] != 0 else 0

        # Determine crystal shape
        shape = self.get_shape_class(aspect1, aspect2)

        sa_hull, vol_hull, sa_vol = None, None, None
        if get_sa_vol:
            sa_vol_vals = self.get_sa_vol_ratio()
            sa_hull, vol_hull, sa_vol = (
                sa_vol_vals[0],
                sa_vol_vals[1],
                sa_vol_vals[2],
            )

        return self.shape_tuple(
            x=lengths[0],
            y=lengths[1],
            z=lengths[2],
            pc1=sorted_pca[0],
            pc2=sorted_pca[1],
            pc3=sorted_pca[2],
            aspect1=aspect1,
            aspect2=aspect2,
            sa=sa_hull,
            vol=vol_hull,
            sa_vol=sa_vol,
            shape=shape,
        )
