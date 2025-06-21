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
    metadata = out_dir / "metadata.json"
    assert metadata.exists()
