import asyncio
from pathlib import Path

import pytest

from modules import dataset_generator


@pytest.mark.asyncio
async def test_generate_dataset(tmp_path: Path):
    out_dir = tmp_path / "out"
    result = await dataset_generator.generate_dataset(
        str(out_dir), size_gb=0.000001, chunk_size=2
    )
    assert "Dataset generated" in result
    metadata_path = out_dir / "metadata.json"
    assert metadata_path.exists()

    # verify compressed chunk created
    compressed_files = list((out_dir / "compressed").glob("chunk_*" + dataset_generator.COMPRESSED_EXTENSION))
    assert compressed_files, "compressed chunks not found"

    metadata = await dataset_generator.read_metadata(out_dir)
    assert metadata["compression"] == "gzip"
    assert metadata["chunk_extension"] == dataset_generator.COMPRESSED_EXTENSION
    assert metadata["total_size_bytes"] > 0
