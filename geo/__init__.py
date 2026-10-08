"""Geometry support: quads, planar pose, plane fitting."""
from geo.quad import order_corners, quad_side_lengths, mean_side_px, quad_area, convex_quad
from geo.pose import camera_matrix, pose_from_marker, plane_to_image_homography
from geo.plane import fit_plane, plane_residuals

__all__ = [
    "order_corners", "quad_side_lengths", "mean_side_px", "quad_area", "convex_quad",
    "camera_matrix", "pose_from_marker", "plane_to_image_homography",
    "fit_plane", "plane_residuals",
]
