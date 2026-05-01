"""
View selection module.
For each registered reference image, selects source views for MVS based on
sparse point visibility overlap.
"""

import os
import json
from mvs.read_sfm import read_sfm_results


def select_source_views_by_visibility(tracks, image_names, source_view_num=3, logger=None):
    """Select source views for each reference image based on sparse point visibility overlap.

    For each reference image, count the number of shared 3D points with every other image.
    Select the top source_view_num images with the most shared points.

    Args:
        tracks: dict mapping point_id -> [(img_name, kp_idx), ...].
        image_names: Sorted list of registered image filenames.
        source_view_num: Number of source views to select (default 3).
        logger: Optional logger instance.

    Returns:
        dict: {ref_img: [src_img1, src_img2, src_img3]}
        dict: {img_name: set of visible point_ids}
    """
    # Build visibility sets: which images see which points
    # Also build image -> set of visible point ids
    image_points = {img: set() for img in image_names}

    for pt_id, observations in tracks.items():
        for img_name, kp_idx in observations:
            if img_name in image_points:
                image_points[img_name].add(pt_id)

    # Build overlap matrix
    view_pairs = {}
    for ref_name in image_names:
        ref_points = image_points.get(ref_name, set())
        if len(ref_points) == 0:
            # Fallback: use neighboring images by name order
            idx = image_names.index(ref_name)
            n = len(image_names)
            sources = []
            for offset in range(1, source_view_num + 1):
                fwd = image_names[(idx + offset) % n]
                if fwd not in sources:
                    sources.append(fwd)
                if len(sources) >= source_view_num:
                    break
                bwd = image_names[(idx - offset) % n]
                if bwd not in sources:
                    sources.append(bwd)
            view_pairs[ref_name] = sources[:source_view_num]
            continue

        overlap_counts = []
        for other_name in image_names:
            if other_name == ref_name:
                continue
            other_points = image_points.get(other_name, set())
            overlap = len(ref_points & other_points)
            overlap_counts.append((overlap, other_name))

        # Sort by overlap count descending
        overlap_counts.sort(key=lambda x: -x[0])
        sources = [name for _, name in overlap_counts[:source_view_num]]

        view_pairs[ref_name] = sources

        if logger:
            overlaps_str = ", ".join([f"{name}:{cnt}" for cnt, name in overlap_counts[:source_view_num]])
            logger.info(f"  {ref_name} ({len(ref_points)} pts): sources = [{overlaps_str}]")

    return view_pairs, image_points


def export_view_pairs(view_pairs, output_path, logger=None):
    """Export view pairs to JSON.

    Args:
        view_pairs: dict {ref_img: [src_img1, src_img2, ...]}
        output_path: Path to output JSON file.
        logger: Optional logger instance.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(view_pairs, f, indent=2)

    if logger:
        logger.info(f"Exported view pairs for {len(view_pairs)} images to {output_path}")
