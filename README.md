# DeskGuard – AI-Powered Workspace Asset Verification System

**HackZen 2026 Open Challenge Submission**
**Team:** TriSight AI
**Members:** Dhakshitha · Harini · Sadurthiya

---

## Problem Statement

Hybrid and hot-desk workplaces make it easy to forget or misplace the physical
items a workstation needs before someone can actually start working — a
laptop or monitor, a keyboard, a mouse, a water bottle. Manually checking a
desk against a checklist is slow, easy to skip, and doesn't scale across many
workstations. There is no lightweight, camera-based way to automatically
confirm "is this desk actually ready to work at?"

## Objective

Build a real-time computer vision system that watches a workspace through a
webcam, automatically verifies that a fixed set of required assets is
present, flags anything missing, and warns about unexpected/foreign objects
on the desk — all through a simple desktop interface.

## Why DeskGuard?

DeskGuard automates workspace readiness verification using computer vision, reducing manual inspection and providing instant feedback on missing or unexpected items. It demonstrates a practical application of AI in office automation.

## Proposed Solution

DeskGuard runs a pretrained object detection model on a live webcam feed,
compares what it sees against four required-asset rules, and reports a clear
Ready / Not Ready / Ready-with-Warnings status in a PyQt5 desktop app, along
with per-object confidence scores, a live annotated video feed, and an audit
trail (CSV log + screenshot capture) for every verification run.

**Verification rules:**
1. A Laptop **or** Monitor must be present (either satisfies the rule).
2. A Keyboard must be present.
3. A Mouse must be present.
4. A Water Bottle must be present.
5. Duplicate detections of the same object are ignored — only presence matters.
6. Detection confidence scores are ignored when deciding pass/fail (shown in
   the UI for transparency only, not used as a threshold for the verdict).
7. Any detected object outside the above list is reported as an "unexpected
   object" (a warning, not a failure, unless assets are also missing).

---

## Technologies Used

| Component | Technology |
|---|---|
| Object detection | [Ultralytics YOLOv8](https://docs.ultralytics.com/models/yolov8) (pretrained) |
| Language | Python 3.12 |
| Computer vision / camera I/O | OpenCV |
| Desktop GUI | PyQt5 |
| Logging | loguru |
| Data handling | pandas, NumPy |
| Image handling | Pillow |

## Dataset

No custom dataset was collected or trained on for this challenge. Detection
runs on YOLOv8's **official pretrained weights**, trained by Ultralytics on
the **COCO dataset** (Common Objects in Context, Microsoft) — an 80-class
general object detection benchmark that already includes the classes this
project relies on: `laptop`, `tv` (used for monitors), `keyboard`, `mouse`,
and `bottle`.

## Methodology / Model Architecture

```
Webcam Frame
     │
     ▼
┌─────────────────────────┐
│  AssetDetector           │  YOLOv8 (Ultralytics) inference
│  (src/detector.py)       │  → list of {label, confidence, bbox}
└─────────────────────────┘
     │
     ▼
┌─────────────────────────┐
│  AssetVerifier            │  Compares detected labels against
│  (src/verifier.py)        │  the 4 fixed required-asset rules
└─────────────────────────┘
     │
     ▼
┌─────────────────────────┐
│  MainWindow (PyQt5 GUI)   │  Live annotated feed + status panel
│  (src/gui.py)             │  showing Ready/Not Ready/Warnings,
└─────────────────────────┘  detected/missing/unexpected items
     │                       with confidence scores
     ▼
 CSV audit log (output/verification_log.csv)
```

1. `detector.py` loads YOLOv8 and runs inference on each webcam frame,
   returning every detection's class label, confidence score, and bounding box.
2. `verifier.py` reduces detections to a unique set of labels (ignoring
   duplicates and confidence), checks them against the four required-asset
   rules, and returns a structured result: `status`, `detected_assets`,
   `missing_assets`, `unexpected_objects`.
3. `gui.py` renders the live feed with bounding-box overlays, and displays
   the verification result with a confidence score attached to each
   detected/unexpected item, formatted as one of DeskGuard's four defined
   states:
   - 🟢 **Workspace Ready** — all required assets present, nothing unexpected.
   - 🟡 **Workspace Ready with Warnings** — all required assets present, but
     unexpected objects are also on the desk.
   - 🔴 **Workspace Not Ready** — one or more required assets missing
     (whether or not unexpected objects are also present).
4. Every verification run is appended to `output/verification_log.csv` for
   auditing, and screenshots can be saved on demand.

**Known limitation:** because YOLOv8 is a closed-set detector pretrained on
COCO, it can only ever label an object as one of COCO's 80 fixed classes.
An object outside that list (e.g. a mango, a stapler) will either go
undetected or get mislabeled as the visually closest COCO class — see
[Future Scope](#future-scope) for how this could be addressed.

---

## Installation & Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/Dhakshitha178/DeskGuard-TriSightAI.git
   cd DeskGuard-TriSightAI
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Model weights**
   No manual download needed — on first run, Ultralytics automatically
   downloads `yolov8n.pt` into `assets/models/`. An internet connection is
   required for this first launch only.

5. **Run the application**
   ```bash
   python main.py
   ```

---

## Usage Instructions

1. Launch the app with `python main.py` — the DeskGuard window opens.
2. Click **Start Monitoring** to load the model and begin reading from your
   default webcam (`CAMERA_INDEX` in `src/config.py` if you need to change
   which camera is used).
3. The left panel shows the live camera feed with bounding boxes drawn
   around every detected object.
4. The right panel's **Verification Status** box updates continuously with:
   - Current status header (🟢 / 🟡 / 🔴)
   - **Detected Assets** — each required asset found, with its confidence
     score, e.g. `✓ Laptop/Monitor (92%)`
   - **Missing Assets** — required assets not currently visible
   - **Unexpected Objects** — anything detected that isn't a required
     asset, with its confidence score
   - A closing message telling you whether you're clear to start work
5. Click **Save Screenshot** at any time to save the current annotated
   frame to `screenshots/`.
6. Click **Stop Monitoring** to release the camera.
7. Every check is also appended to `output/verification_log.csv` for later
   review.

---

## Results and Outputs

- Live bounding-box overlays on the video feed for every detected object.
- Real-time status panel cycling through the four DeskGuard states as
  objects are added to or removed from the desk.
- Example log row from `output/verification_log.csv`:

  | timestamp | status | detected_assets | missing_assets | unexpected_objects |
  |---|---|---|---|---|
  | 2026-07-12 14:02:31 | NOT_READY | Keyboard, Mouse | Laptop/Monitor, Water Bottle | person |

- Screenshots captured on demand in `screenshots/`, useful for audit trails
  or demo material.



---

## Future Scope

- **Open-vocabulary detection** (e.g. YOLOE) to correctly label objects
  outside COCO's fixed 80 classes (fruits, stationery, personal items, etc.)
  instead of missing or mislabeling them.
- Multi-camera / multi-desk support for monitoring several workstations
  from one dashboard.
- Cloud-based logging and a web dashboard for facilities teams.
- Configurable/editable required-asset rules through the GUI instead of
  hardcoded values in `verifier.py`.
- Mobile companion app for remote status checks.

---

## Acknowledgments / Third-Party Attributions

This project uses the following third-party libraries, pretrained models,
and datasets, in accordance with the challenge's attribution requirements:

- **[Ultralytics YOLOv8](https://docs.ultralytics.com/models/yolov8)** —
  pretrained object detection model, licensed under AGPL-3.0. Used as-is
  for inference; not fine-tuned or retrained.
- **[COCO Dataset](https://cocodataset.org/)** (Common Objects in Context) —
  the dataset Ultralytics' YOLOv8 pretrained weights were trained on.
  © Microsoft, used under its respective license terms.
- **[OpenCV](https://opencv.org/)** — video capture and image processing.
- **[PyQt5](https://www.riverbankcomputing.com/software/pyqt/)** — desktop
  GUI framework.
- **[loguru](https://github.com/Delgan/loguru)** — application logging.
- **[pandas](https://pandas.pydata.org/)** / **[NumPy](https://numpy.org/)** —
  data handling.
- **[Pillow](https://python-pillow.org/)** — image handling.

No proprietary code, datasets, or assets were used. All third-party
components above are open-source and used under their respective licenses.

## References

- Ultralytics YOLOv8 Documentation: https://docs.ultralytics.com/models/yolov8
- COCO Dataset: https://cocodataset.org/
- PyQt5 Documentation: https://www.riverbankcomputing.com/static/Docs/PyQt5/

---

## Project Structure

```
DeskGuard-TriSightAI/
├── assets/            # Logo, icons, model weights (auto-downloaded)
├── docs/              # Design notes and documentation
├── output/            # Generated verification logs
├── screenshots/        # Captured screenshots
├── src/
│   ├── __init__.py
│   ├── detector.py    # YOLOv8-based object detection
│   ├── verifier.py    # Fixed-rule asset verification logic
│   ├── gui.py         # PyQt5 desktop interface
│   ├── utils.py       # Shared helper functions
│   ├── config.py      # Centralized configuration
│   └── app.py         # Application bootstrap
├── requirements.txt
├── README.md
├── LICENSE
├── .gitignore
└── main.py            # Entry point
```

---

## Team & Ownership

| Member | Primary Ownership |
|---|---|
| Dhakshitha | Detection pipeline (`detector.py`), model tuning |
| Harini | Verification logic (`verifier.py`), data/logging layer |
| Sadurthiya | GUI (`gui.py`) and application integration (`app.py`, `main.py`) |

All members share ownership of `config.py`, `requirements.txt`, and code review.

---

## License
This project is licensed under the terms of the [MIT License](LICENSE).
