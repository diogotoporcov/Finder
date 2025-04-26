from pathlib import Path
from typing import Dict, Tuple, Optional, List

import numpy as np

from finder.utils.utils import FilePath


def calc_similarity(
        vector1: np.ndarray,
        vector2: np.ndarray,
        cosine_penalty_factor: float = 4,
        euclidean_penalty_factor: float = 0.1
) -> float:
    # Cosine similarity
    cosine_sim = np.dot(vector1, vector2) / (np.linalg.norm(vector1) * np.linalg.norm(vector2))
    cosine_distance = 1 - cosine_sim

    # Euclidean distance
    euclidean_distance = np.linalg.norm(vector1 - vector2)

    # Adjusted similarities
    adjusted_cosine_similarity = np.exp(-cosine_penalty_factor * cosine_distance)
    adjusted_euclidean_similarity = 1 / (1 + euclidean_penalty_factor * euclidean_distance)

    # Combined similarity
    combined_similarity = (adjusted_cosine_similarity + adjusted_euclidean_similarity) / 2

    return combined_similarity


def calc_similarities(
        reference_vector: np.ndarray,
        vectors: Dict[Path, np.ndarray],
        *,
        min_similarity: Optional[float] = 0.2,
        max_similarity: Optional[float] = 0.9,
        cosine_penalty_factor: float = 4,
        euclidean_penalty_factor: float = 0.2
) -> List[Tuple[FilePath, float]]:
    comparison_results = []

    for path, vector in vectors.items():
        similarity = calc_similarity(reference_vector, vector, cosine_penalty_factor, euclidean_penalty_factor)

        if min_similarity and similarity < min_similarity:
            continue

        if max_similarity and similarity >= max_similarity:
            return [(path, similarity)]

        comparison_results.append((path, similarity))

    comparison_results.sort(key=lambda x: x[1], reverse=True)

    return comparison_results
