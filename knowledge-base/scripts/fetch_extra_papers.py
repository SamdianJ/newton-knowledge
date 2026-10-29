"""Explicit evidence acquisition; rebuilding the knowledge base never downloads."""

import hashlib
import json
import ssl
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PAPERS = [
    (
        "mujoco-2012",
        "mujoco",
        "MuJoCo: A physics engine for model-based control",
        2012,
        "https://roboti.us/lab/papers/TodorovIROS12.pdf",
        "引擎架构与广义坐标动力学背景；不代表 1.7.0 封装的参数默认值。",
    ),
    (
        "mujoco-2014",
        "mujoco",
        "Convex and analytically-invertible dynamics with contacts and constraints: Theory and implementation in MuJoCo",
        2014,
        "https://roboti.us/lab/papers/TodorovICRA14.pdf",
        "软约束与可逆接触动力学的机制背景；现代后端支持需查固定源码。",
    ),
    (
        "kamino-loops-2025",
        "kamino",
        "On Solving the Dynamics of Constrained Rigid Multi-Body Systems with Kinematic Loops",
        2025,
        "https://arxiv.org/pdf/2504.19771v1",
        "最大坐标、闭环机械系统与对偶接触求解；Kamino 源码直接引用。",
    ),
    (
        "proximal-admm-2024",
        "kamino",
        "From Compliant to Rigid Contact Simulation: a Unified and Efficient Approach",
        2024,
        "https://arxiv.org/pdf/2405.17020v1",
        "近端 ADMM、接触锥投影及残差控制背景；Kamino 源码直接引用。",
    ),
]


def main():
    context = ssl.create_default_context()
    if hasattr(ssl, "enum_certificates"):
        for certificate, encoding, trust in ssl.enum_certificates("ROOT"):
            if encoding == "x509_asn" and (trust is True or ssl.Purpose.SERVER_AUTH.oid in trust):
                context.load_verify_locations(cadata=ssl.DER_cert_to_PEM_cert(certificate))
    records = []
    for key, solver, title, year, url, role in PAPERS:
        directory = ROOT / "sources/papers" / key
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "paper.pdf"
        if not path.exists():
            with urlopen(
                Request(url, headers={"User-Agent": "NewtonKnowledge/1.0 research"}), timeout=50, context=context
            ) as response:
                data = response.read()
            if not data.startswith(b"%PDF"):
                raise ValueError("Not a PDF: " + url)
            path.write_bytes(data)
        reader = PdfReader(path)
        pages = [page.extract_text() or "" for page in reader.pages]
        (directory / "text.txt").write_text(
            "\n\n".join(f"--- PAGE {i} ---\n{page}" for i, page in enumerate(pages, 1)), encoding="utf-8"
        )
        doi = {
            "mujoco-2012": "10.1109/IROS.2012.6386109",
            "mujoco-2014": "10.1109/ICRA.2014.6907751",
            "kamino-loops-2025": "10.48550/arXiv.2504.19771",
            "proximal-admm-2024": "10.48550/arXiv.2405.17020",
        }[key]
        records.append(
            {
                "id": "paper:" + key,
                "solver": solver,
                "title": title,
                "year": year,
                "url": url,
                "doi": doi,
                "role": role,
                "local_path": path.relative_to(ROOT).as_posix(),
                "text_path": (directory / "text.txt").relative_to(ROOT).as_posix(),
                "pages": len(pages),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "acquired_at": datetime.now(timezone.utc).isoformat(),
                "evidence_type": "paper_background",
                "rights": "Original authors/publishers retain rights.",
            }
        )
        print(key, len(pages), "pages")
    (ROOT / "manifests/extra-papers.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
