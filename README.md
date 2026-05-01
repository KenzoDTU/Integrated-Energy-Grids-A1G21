# Integrated-Energy-Grids-A1G21
46770 - Integrated Energy Grids - Assignment 1

## Setup

**1. Create and activate a virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
.venv\Scripts\activate           # Windows
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Register the kernel with Jupyter**

```bash
python -m ipykernel install --user --name=.venv --display-name "Python (.venv)"
```

**4. Launch JupyterLab**

```bash
jupyter lab
```

Select the **Python (.venv)** kernel when opening a notebook.

## Notebooks

Each step of the assignment is implemented in its own notebook:

| Notebook | Description |
|----------|-------------|
| `step_A.ipynb` | Step A |
| `step_B.ipynb` | Step B |
| `step_C.ipynb` | Step C |
| `step_D.ipynb` | Step D |
| `step_E.ipynb` | Step E |
| `step_F.ipynb` | Step F |
| `step_G.ipynb` | Step G |
| `step_H.ipynb` | Step H |
| `step_I.ipynb` | Step I |
| `step_J.ipynb` | Step J |
| `data.ipynb`   | Data preprocessing |

Run notebooks in alphabetical order (A → J) as later steps may depend on outputs from earlier ones.
