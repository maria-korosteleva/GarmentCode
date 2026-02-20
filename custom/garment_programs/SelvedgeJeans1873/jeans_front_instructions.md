# Drafting the Jeans Front Panel (1873 Style)

Step-by-step instructions adapted from Historical Tailoring Masterclasses.

## Measurements Required

| Measurement | Description |
|---|---|
| Side length | Outside leg, waist to floor |
| Inseam | Crotch to floor, inside leg |
| Seat | Circumference around fullest part of seat |
| Hem width | Desired hem opening width |
| Knee width | Desired knee opening width |

## Step 1: Marking Out the Lengths

Draw a long horizontal baseline. Mark point **0** at the right end (this is the hem). From **0**, measure left to mark:

- **0 → 1**: Side length (waist point). The side length measurement should not include the waistband.
- **0 → 2**: Inseam measurement (crotch point)
- **0 → 3**: Half of 0–2 distance, plus 2" (knee point)
- **2 → 4**: Half the seat divided by 6, measured from 2 toward the waist (hip point)

Result (left to right): **1 — 4 — 2 — 3 — 0**

## Step 2: Marking Out the Widths

Square down (perpendicular to baseline) from each point:

- From **0**: half the hem width minus 3/8"
- From **3**: half the knee width minus 3/8"
- From **2** down by **seat / 4** → mark as **point 5**
- From **5** down by **(seat/2) / 6 minus 1"** → mark as **point 6** (crotch extension)
- From **4** and **1**: drop the same distance as 2–5 (seat/4)
  - The drop from **1** becomes **point 7** (inner waist)
  - Square left from **5** along the horizontal to the vertical from **4** → **point 8**

Points 5, 7, and 8 lie on the same horizontal line (the seat width level).

## Step 3: Point Adjustments

Fine-tune three points:

1. From **point 1**, measure down **3/8"** and mark the adjusted point.
2. From **point 7**, measure **3/8"** toward point 8 (horizontally). Then square up **5/8"** (toward baseline) to find the adjusted point.
3. Draw a line at **45 degrees down-left** from **point 5**. Mark **point 9** at half the distance of 5-to-6 along this line.

## Step 4: Construction Lines

Draw two construction lines to guide the curves:

1. **Fly line**: From the adjusted point near **7**, draw a straight line through **point 8** and extend slightly beyond. This establishes the front fly/rise line.
2. **Inseam line**: Draw a line from **point 6** through the knee drop at **3** to the hem drop at **0**. This guides the inseam.

## Step 5: Curves

Draw the following curves using a hip curve, French curve, or freehand:

1. **Side hip curve (1 → 4)**: Shallow curve for the hip area, gently tapering into the side seam line a little above point 4.
2. **Front rise curve (1 → 7)**: Shallow curve from adjusted 1 to adjusted 7 (the "hip line"). Make intersections at both ends as close to right angles as possible.
3. **Crotch curve (8 → 9 → 6)**: Curve from point 8 through point 9 to point 6.
4. **Inseam curve (6 → 3)**: From point 6 to the knee, gradually shaping into the straight line below the knee. At point 6, try to get the crotch and inseam curves to meet at right angles.

## Step 6: Center Front Line

Find the distance between points **2** and **5**. Divide by **2** and make a temporary mark. Measure **3/4" toward point 2** to find **point 10** (center front).

## Style Variations

- **1873 straight leg**: Hem width matches knee width for a square, full cut.
- **Tapered**: Reduce the hem width for a more fitted look below the knee.
- **Boot cut**: Fitted at the knee but wider at the hem to fit over boots.

## Note: Relationship to Garmentcode Library Measurements

The garmentcode library (`pygarment`) defines its own body parametrization system
via `BodyParametrizationBase` in `pygarment/garmentcode/params.py`. Library body
files (`assets/bodies/*.yaml`) contain ~25 SMPL-derived measurements under a
`body:` key (height, waist, hips, bust, shoulder_w, armscye_depth, etc.). These
are anthropometric values extracted from 3D body scans, used by the library's
built-in garment programs (bodice, tee, meta_garment).

**Our custom jeans programs bypass this system entirely.** `jeans_front.py` has
its own `load_measurements()` that reads a different YAML format (`measurements:`
key, with a `unit` field for inch/cm conversion) and expects traditional tailoring
measurements specific to trouser drafting.

### Overlap between the two systems

| Jeans measurement | Library equivalent | Notes |
|---|---|---|
| `waist` | `waist` | Same concept (circumference) |
| `seat` | `hips` | Same concept (hip circumference) |
| `side_length` | — | Could be derived from `height`, `waist_line`, `head_l` but not directly available |
| `inseam` | — | Not in library; related to `_leg_length` (computed) but not the same |
| `hem_width` | — | Design choice, not a body measurement |
| `knee_width` | — | Design choice, not a body measurement |

### Why we don't use library measurements

1. **Missing keys**: side_length, inseam, hem_width, and knee_width have no
   library equivalents. They are either traditional tape measurements or design
   decisions, not scannable body dimensions.
2. **Different context**: The library measurements come from SMPL body model
   fitting. Our measurements are taken with a tape measure or from a size chart
   — simpler but differently structured.
3. **Unit handling**: The library works in cm natively. Our loader supports an
   explicit `unit` field for inch-to-cm conversion at load time.

If the jeans programs ever need to accept library body files as input, a thin
adapter mapping `hips` -> `seat` and deriving `side_length`/`inseam` from
height-based calculations would be needed.
