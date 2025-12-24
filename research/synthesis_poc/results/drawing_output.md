# Engineering Drawing
**Course Code: MR/ES/CE/RN 156**

**Study Slides Compiled By:**
*   Mr. Obed Ofori Yemoh
*   Mechanical Eng. Dept.
*   Mob: 0242664193
*   WhatsApp: 0243066123
*   Email: ooyemoh@umat.edu.gh

[Visual Description: Title slide featuring a background of various engineering blueprints and technical drawings. A yellow pencil and a compass are visible on the drawings. The logo of the University of Mines and Technology (UMaT) is in the bottom left corner.]

---

## Course Outline
*   Lesson 1: Introduction to AutoCAD
*   Lesson 2: Conventional Representation
*   Revision: Orthographic Projection
*   Lesson 3: Sections
*   Lesson 4: Assembly Drawings
*   Lesson 5: Projection of Solids
*   Lesson 6: Development of Solids/Surfaces
*   Lesson 7: Curves of Intersection

[Visual Description: Slide showing the course outline alongside a 3D rendering of mechanical gears, a yellow hard hat, a vernier caliper, a pencil, and a ruler resting on a blueprint.]

---

## Course Objectives
*   **Objective 1:** To understand the conventional symbols and how to use them in detail drawings.
*   **Objective 2:** To understand what sectioning a part or assembly is and when to apply them.
*   **Objective 3:** To understand the term assembly drawings, types of assembly drawings and how to assemble parts together, creating part lists.
*   **Objective 4:** To be enlightened about the need to develop solids and how to develop various shades of solids.
*   **Objective 5:** To understand what CAD is, the various kinds of CAD software and their applications.

---

# Lesson 1: Introduction to AutoCAD

### Skills Covered:
*   User Interface and Templates.
*   Drawing and Modifying Tools.
*   Text, Dimension and Tables.
*   Layers, Title Block and Viewport Creation.
*   Drawing with AutoCAD.

[Visual Description: Background image of a technical drawing with a compass, pencil, eraser, and protractor. Dimensions like $\phi 145$, $\phi 130$, and $\phi 65$ are visible.]

### What is AutoCAD?
Automatic Computer Aided Drawing/Drafting software, as its full name reads, is a computer software used for drawing and designing. It is the most widely used drafting software in the world of Engineering. It can also be used by other Drawing Professionals like Graphic Designers, Fashionistas, Interior Designers, Landscapers, and Educators.

---

### User Interface – Start Page
The AutoCAD interface includes several key areas:
*   **Quick Select Toolbar:** Top left, for common file operations.
*   **Info Center:** Top right, for help and account info.
*   **Ribbon:** The main toolbar containing tabs like Home, Insert, Annotate, etc.
*   **File Tabs:** Allows switching between open drawings.
*   **Viewport Controls:** Top left of the drawing area.
*   **View Cube:** Top right of the drawing area for 3D navigation.
*   **Navigation Bar:** Right side of the drawing area.
*   **Cursor:** The crosshairs used for drawing.
*   **Coordinate Symbol (UCS):** Bottom left of the drawing area.
*   **Command Panel:** Bottom area for typing commands.
*   **Model/Layout Tabs:** Bottom left, for switching between model space and paper space.
*   **Status Bar:** Bottom right, containing accuracy tools and drawing aids.

[Visual Description: Screenshots of the AutoCAD 2022 Start Page and the main workspace with labels for the UI components mentioned above.]

---

### Accuracy Tools / Drawing Aids
*   **Grid:** Toggled using the **F7** key. Displays a grid pattern in the drawing area.
*   **Snap Mode:** Toggled using the **F9** key. Restricts cursor movement to specified intervals.
*   **Ortho Mode:** Toggled using the **F8** key. Restricts drawing to vertical or horizontal lines.
*   **Polar Tracking:** Toggled using the **F10** key. Displays alignment paths at specified angles.
*   **Object Snap Tracking:** Toggled using the **F11** key. Allows drawing lines at exact coordinate points and precise angles relative to existing objects.
*   **2D Object Snap (OSNAP):** Toggled using the **F3** key. Snaps the cursor to specific points on objects (e.g., endpoint, midpoint, center).
*   **Isoplane:** Cycles through 2-1/2D isoplane settings.
*   **Dynamic UCS:** Turns on UCS alignment with planar surfaces.
*   **Dynamic Input:** Displays distances and angles near the cursor and accepts input using the Tab key.

---

### Drawing Tools
1.  **Line:** Invoke using the `LINE` or `L` command. Specify a starting point and a second point. Terminate with ENTER, ESC, or SPACEBAR.
2.  **Circle:** Invoke using the `CIRCLE` command. Can be drawn using six methods: center/radius, center/diameter, 2 points, 3 points, tan/tan/radius, or tan/tan/tan.
3.  **Rectangle:** Specify two opposite corners, or define by area, dimensions, or rotation.
4.  **Polyline:** Invoke using `PLINE`. A single object consisting of line and arc segments. Can have varying thicknesses.
5.  **Arc:** Used to create an arc through various methods (e.g., 3-point, start/center/end).
6.  **Polygon:** Used to draw regular polygons with 3 or more sides.
7.  **Spline:** Used for drawing smooth, wavy lines through fit points.
8.  **Donut:** Creates a filled circle or a wide ring.
9.  **Ellipse:** Creates an ellipse or an elliptical arc.

[Visual Description: Screenshot of the "Draw" panel in the AutoCAD ribbon showing icons for Line, Polyline, Circle, Arc, Rectangle, and Ellipse.]

---

### Modifying Tools
1.  **Move:** Moves objects from current location to a new location without changing size or orientation.
2.  **Copy:** Creates duplicates of selected objects.
3.  **Rotate:** Rotates objects around a base point. Positive angles are counterclockwise; negative angles are clockwise.
4.  **Mirror:** Creates a mirrored copy of selected objects across a specified mirror line.
5.  **Scale:** Changes the size of objects.
6.  **Trim:** Removes unwanted portions of objects that extend beyond a cutting edge.
7.  **Extend:** Extends objects to meet a boundary edge.
8.  **Fillet:** Rounds the corners between two entities.
9.  **Chamfer:** Bevels the edges of objects.
10. **Rectangular Array:** Creates copies in rows, columns, and levels.
11. **Polar Array:** Copies objects around a center point in a circular pattern.
12. **Erase:** Removes unwanted objects.
13. **Explode:** Breaks a compound object (like a polyline or block) into its component parts.
14. **Offset:** Creates parallel lines, concentric circles, or parallel curves at a specified distance.
15. **Break:** Breaks an object between two points.
16. **Join:** Combines series of finite linear and open curved objects at common endpoints.

[Visual Description: Screenshot of the "Modify" panel in the AutoCAD ribbon showing icons for Move, Copy, Stretch, Rotate, Mirror, Scale, Trim, Fillet, and Array.]

---

### Setting Text Style
1.  Enter `st` (Style) at the keyboard.
2.  In the **Text Style** dialog, set **Height** to 6 and select **Arial** from the Font name list.
3.  Click **New**, name it "Arial", and click OK.
4.  Click **Set Current** and then **Close**.

### Setting Dimension Style
1.  Enter `d` at the keyboard to open the **Dimension Style Manager**.
2.  Click **Modify**.
3.  In the **Symbols and Arrows** tab, make necessary settings.
4.  In the **Line** tab, set color to Magenta.
5.  In the **Text** tab, set style to Arial, color to Magenta, height to 6, and check the **ISO** box.
6.  In the **Primary Units** tab, set **Precision** to 0 and **Decimal separator** to Period.
7.  Click **New** to create a style named "My-style", click **Continue**, then **Set Current** and **Close**.

[Visual Description: Screenshots of the Text Style and Dimension Style Manager dialog boxes in AutoCAD.]

---

### Setting Layers (Layer Properties Manager)
1.  Enter `layer` or `la` at the keyboard.
2.  Click **New Layer** and name it "Centre".
3.  Repeat to create layers: "Construction", "Dimensions", "Hidden", and "Text".
4.  Assign colors to each layer by clicking the square in the **Color** column.
5.  For the "Centre" layer, click **Continuous** in the Linetype column, click **Load**, select **CENTER2**, and click OK.
6.  For the "Hidden" layer, load and select **HIDDEN2**.
7.  Set **Lineweight** to 0.7 for Layer 0 and 0.3 for all others except Text.

[Visual Description: Screenshot of the Layer Properties Manager showing columns for Name, On, Freeze, Lock, Color, Linetype, and Lineweight.]

---

### Drawing Templates
*   Templates are files with a `.dwt` extension.
*   They contain predetermined settings like Grid spacing, Snap, Text styles, and Dimension styles.
*   **acad.dwt:** Uses inches and feet.
*   **acadiso.dwt:** Uses millimeters and meters.
*   Check units using the `UNITS` command.

### Creating a Customized Template
1.  Open AutoCAD, right-click the **Start Tab**, and click **NEW**.
2.  Select `acadiso.dwt`.
3.  Type `Z` (Zoom) then `A` (All).
4.  Set Layers, Text Styles, and Dimension Styles.
5.  Go to **Layout 1** tab, right-click, and select **Page Setup Manager**.
6.  Click **Modify**, select Plotter/Printer, Paper size, and Orientation.
7.  Create a boundary and Title block using drawing tools.
8.  Set a Viewport using the `MV` or `MVIEW` command.
9.  Save as a template (`.dwt`) using **SAVE AS**.

---

### Exercise: 2D Drawing
[Visual Description: Two complex 2D mechanical profiles for practice. 
Left profile: A bracket-like shape with multiple circular holes ($\phi 20$, $\phi 32$), rounded corners ($R10$, $R20$, $R32$), and a large fillet ($R70$). Overall width is 76 units, height is 64 units.
Right profile: A sector-like shape with concentric arcs ($R50$, $R63$, $R76$), a central hub ($\phi 15$, $\phi 25$), and two small holes ($2 \times \phi 10$) on a flange. Angles of $105^\circ$ and $30^\circ$ are specified.]

---

# Lesson 2: Conventional Representation

### Introduction
Many common engineering features are difficult and tedious to draw in full. To save time and space, they are represented in simple conventional forms.

*   **External Screw Threads:** Crests are defined by a continuous thick line; roots by a parallel continuous thin line. The distance between them is approx. $1/8$ of the major diameter.
*   **Internal Screw Threads:** Tapped holes show thick outlines for the drill hole and thin lines for the thread roots.
*   **Screw-thread Assembly:** The male thread takes precedence over the female thread. Hatching lines do not cross thick lines.
*   **Interrupted Views:** Long components are shown partially using thin, continuous break lines to save space.
*   **Cylindrical Compression Springs:** Coils are drawn only at the ends, connected by parallel thin chain lines.
*   **Splined and Serrated Shafts:** Only a few splines are shown; the root circle is a thin circle.
*   **Knurling (Diamond and Straight):** Provides a rough surface for manual operation.
*   **Holes on Circular/Linear Pitch:** Draw one hole and indicate the positions of the rest.
*   **Spur Gears:** Front view shows the outside thick circle and the pitch 'center-line' circle.
*   **Bearings:** Complicated sectional views are replaced by a rectangle with thin-line diagonals.

[Visual Description: A table showing "Title", "Subject" (3D view), and "Convention" (2D drawing) for features like external/internal threads, assemblies, interrupted views, squared ends, splined/serrated shafts, knurling, holes on pitch, springs, gears, and bearings. Real-world photos of these components are also provided for reference.]

---

### Exercises: Conventional Representation
1.  Produce the Front, Left, and Right End Views of the provided images (a splined shaft assembly and a knurled screw assembly).
2.  **Problem 15.2: Working Drawing of a Hammer.** Prepare a detail drawing for the hammer head (Brass) and two optional handles (SAE 6061-T6). Include dimensions, knurling, and thread specifications (e.g., $1/2-20UNF-2B$).

---

# Revision: Orthographic Projection

### Skills Covered:
*   Producing Orthographic views.
*   First Angle Projection.
*   Third Angle Projection.

[Visual Description: An isometric drawing of a multi-colored stepped block. Arrows indicate the direction of view for projection.]

### Concepts
*   **Glass Box Method:** Imagine the object inside a glass box. Project points onto the faces of the box (Front, Top, Right Side).
*   **Unfolding the Box:** The box is "unfolded" to create a 2D layout of the views.
*   **First Angle Projection:** Common in Europe/Africa. The object is between the observer and the projection plane.
    *   Layout: Top view is below the Front view. Left view is to the right of the Front view.
*   **Third Angle Projection:** Common in USA/Canada. The projection plane is between the observer and the object.
    *   Layout: Top view is above the Front view. Right view is to the right of the Front view.

[Visual Description: Diagrams illustrating the "Glass Box" concept and the resulting layouts for both First and Third Angle Projections.]

---

# Lesson 3: Sectional Views

### Introduction
Sectional views (or cross sections) are used to reveal the internal features of a part that cannot be shown clearly using hidden lines. Imagine slicing through the object like an apple.

### Purpose of Sections:
*   To clarify details.
*   To illustrate internal features clearly.
*   To reduce the number of hidden-detail lines.
*   To facilitate dimensioning of internal features.
*   To show the shape of the cross-section.
*   To show relative positions of parts in an assembly.

### Types of Sections:
1.  **Full Section:** The part is cut fully in half.
2.  **Half Section:** Used for symmetrical objects. One quarter of the object is removed, showing half in section and half as an exterior view. A centerline divides the two halves.
3.  **Broken-out Section:** Only a partial section is used to expose a specific interior shape. It is limited by an irregular break line.
4.  **Revolved Section:** The cross-section of an elongated object (bar, spoke) is revolved $90^\circ$ and drawn directly on the longitudinal view.
5.  **Removed Section:** Similar to a revolved section but drawn outside the main view. Often drawn to an enlarged scale and labeled (e.g., SECTION A-A).
6.  **Offset Section:** The cutting plane is "bent" or offset to include features that do not lie in a straight line. The bends are not shown in the section view.
7.  **Aligned Section:** For parts with angled elements, the cutting plane is bent to pass through the features and then revolved into the original plane.
8.  **Partial View:** Used when space is limited; shows only the necessary features.

[Visual Description: Numerous diagrams illustrating each section type. Examples include a sliced melon, a mechanical pulley in full section, a bracket in half section, and a shaft with a revolved section.]

---

### Rules for Section Views:
*   **Cutting Plane Line:** Shows where the object is cut. It has arrows indicating the direction of sight.
*   **Hatching (Section Lining):**
    *   Drawn with thin lines, usually at $45^\circ$.
    *   Spacing is typically $2.5\text{ mm}$ ($1/10"$).
    *   On a single part, hatching must be in the same direction and parallel.
    *   In assemblies, adjacent parts have hatching in different directions or spacings.
*   **Visible Lines:** Show edges and contours visible behind the cutting plane.
*   **Hidden Lines:** Generally omitted in section views unless necessary for clarity.
*   **Visible Lines in Sectioned Areas:** A visible line can never cross a sectioned area of a single part.
*   **Parts Not Sectioned:** When cut lengthwise, do not section: Spokes, Gear Teeth, Shafts, Fasteners (Bolts, Nuts, Pins, Rivets), and Spindles. Ribs and Webs are also not sectioned when cut flatwise to avoid a false impression of solidity.

[Visual Description: Diagrams showing "Correct" vs "Incorrect" hatching techniques, and an assembly drawing (Figure 22) showing non-sectioned parts like the shaft, key, and nut.]

---

### Sectional View Exercises
1.  **Figure 24:** Sketch the sectional view for six different components shown in orthographic projection.
2.  **Figure 25:** Draw in First-angle projection: (a) Front view, (b) Plan, (c) Sectional end view along X-X. (Scale 1:1).
3.  **Figure 26:** Draw in Third-angle projection: (a) Front view, (b) Plan, (c) Sectional end view along A-A. (Scale 1:1).
4.  **Figure 27:** Draw in Third-angle projection: (a) Sectional front view A-A, (b) Plan, (c) Sectional end view B-B. (Scale 1:1).

---

# Lesson 4: Assembly Drawings

### Introduction
*   **Detail Drawings:** Drawings of individual parts with all information for manufacturing.
*   **Assembly Drawing:** Shows how all parts fit together. Usually contains few hidden lines or dimensions.
*   **Working Drawings:** A complete set including detail drawings, assembly drawings, and a parts list.
*   **Standard Parts:** Items like bolts, screws, and keys that are purchased from vendors. They do not need to be drawn in detail; a written description suffices.

### Types of Assembly Drawings:
1.  **Layout (Design) Assembly:** Informal sketches used during the design phase.
2.  **General Assembly:** Most common; includes balloons and a parts list.
3.  **Detail Assembly (Working-drawing Assembly):** Combines details and assembly on the same sheet.
4.  **Erection Assembly:** Includes dimensions and fabrication specs, often for structural steel or cabinetry.
5.  **Subassembly:** An assembly that forms part of a larger general assembly (e.g., an engine in a car).
6.  **Pictorial Assembly:** 3D representation (isometric or rendered) used in catalogs.

[Visual Description: Examples of assembly drawings: a pump jack (Figure 28), a cross shaft assembly in full section (Figure 29), and a meter shaft with broken-out sections (Figure 30).]

---

### Identification and Parts List
*   **Identification Numbers (Balloons):** Circles containing numbers keyed to the parts list. Connected to parts by leader lines (arrowheads for profiles, dots for surfaces).
*   **Parts List (Bill of Materials - BOM):** A table containing:
    *   Item Number (Find Number).
    *   Quantity Required.
    *   Part or Drawing Number.
    *   Description (Name, size, specs).
    *   Material Identification.
    *   Vendor information (for purchase parts).

[Visual Description: Sample Parts List table showing columns for Item, Qty, Part No, Nomenclature/Description, and Material.]

---

### Assembly Drawing Exercises
1.  **Plumb Bob:** Prepare a working-drawing assembly (detail drawings, assembly, and parts list) on one sheet. Parts: Plumb Bob (Bronze), Cap (Bronze).
2.  **Drill Pump:** Prepare the assembly drawing and BOM. Use multi-view projection. Parts include: Pump Housing, O-ring, Seal, Bushing, Shaft, Paddle Wheel, Cover, and Screws.
3.  **Universal Joint:** Rigid coupling for intersecting shafts. Prepare assembly from provided details of forks, central block, pins, collars, and keys.
4.  **Knuckle Joint:** Pin joint for circular rods. Prepare assembly from details of fork end, eye end, pin, collar, and taper pin.
5.  **Bolts and Nuts:** Practice the approximate method of drawing a hexagonal nut and bolt based on major diameter $d$.
    *   Nut height $\approx 0.8d$.
    *   Nut width across flats $\approx 1.5d + 3\text{ mm}$ (or use $2d$ circle for approximation).

---

# Lesson 5: Projection of Solids

### Classification of Solids
1.  **Polyhedra:** Bounded by plane surfaces (faces) meeting at straight lines (edges).
    *   **Regular Polyhedra:** All faces are equal regular polygons (e.g., Tetrahedron, Hexahedron/Cube, Octahedron).
    *   **Prisms:** Two equal and similar end faces (bases) joined by rectangles or parallelograms. Named by base shape (Triangular, Square, Pentagonal, Hexagonal, Octagonal).
    *   **Pyramids:** A plane figure base and triangular faces meeting at a common point (vertex/apex). The line from apex to base corner is the **slant edge**.
2.  **Solids of Revolution:** Generated by revolving a plane surface about one of its edges.
    *   **Cylinder:** Rectangular surface revolved about one side.
    *   **Cone:** Right-angled triangle revolved about one of its perpendicular sides. The line from apex to base center is the **Axis**.
    *   **Sphere:** Semi-circle revolved about its diameter.
3.  **Frustums and Truncated Solids:**
    *   **Frustum:** Solid cut by a plane parallel to its base.
    *   **Truncated:** Solid cut by a plane inclined to its base.

[Visual Description: 3D renderings of various prisms, pyramids, cylinders, cones, and spheres, as well as diagrams of frustums and truncated solids.]

---

### Orientation and Position in Space
Positions of the axis relative to the Principal Planes (HP - Horizontal Plane, VP - Vertical Plane):
1.  Axis perpendicular to HP and parallel to VP.
2.  Axis perpendicular to VP and parallel to HP.
3.  Axis parallel to both VP and HP.
4.  Axis inclined to both HP and perpendicular to VP [? - likely meant inclined to HP and parallel to VP].
5.  Axis inclined to VP and perpendicular to HP.
6.  Axis inclined to both VP and HP.

### Steps for Drawing Projections:
*   **Step 1:** Draw the view that shows the true shape of the base (e.g., if the axis is perpendicular to HP, draw the Plan first).
*   **Step 2:** Project the other view (Elevation).
*   **Step 3:** If the solid is tilted, tilt the initial projection and project the final views.

[Visual Description: Projections of a cylinder in various orientations relative to the XY reference line.]

---

### Projection Exercises
1.  **Right Circular Cone:** Base $\phi 35\text{ mm}$, height $55\text{ mm}$, resting on HP. Draw projections.
2.  **Pentagonal Pyramid:** Base side $25\text{ mm}$, axis $55\text{ mm}$. Rests on HP with one base corner; one base edge makes $45^\circ$ with HP. Axis is perpendicular to VP.
3.  **Hexagonal Prism:** Base side $25\text{ mm}$, axis $55\text{ mm}$. Resting on HP on one base edge; axis inclined at $30^\circ$ to HP and parallel to VP.
4.  **Cylinder:** $\phi 35\text{ mm}$, axis $55\text{ mm}$. Resting on HP on one generator; axis inclined at $50^\circ$ to VP.

---

# Lesson 6: Development of Solids/Surfaces

### Introduction
A **development** is a flat representation or pattern that, when folded, creates a 3D object. Common in sheet metal fabrication.

### Surface Terminology:
*   **Ruled Surface:** Generated by sweeping a straight line (**generatrix**) along a path.
*   **Plane:** A ruled surface where the generatrix moves along a straight path while remaining parallel.
*   **Single-curved Surface:** A developable ruled surface (e.g., Cylinder, Cone).
*   **Double-curved Surface:** Generated by a curved line; has no straight-line elements (e.g., Sphere, Torus). Non-developable; must be approximated.
*   **Warped Surface:** A ruled surface that is not developable (e.g., airplane exterior surfaces).

### Methods of Development:
1.  **Parallel-line Development:** For prisms and cylinders (edges/generators are parallel).
2.  **Radial-line Development:** For pyramids and cones (lines radiate from an apex).
3.  **Triangulation Development:** For transition pieces.
4.  **Approximate Development:** For spheres.

[Visual Description: Diagrams showing the "unrolling" of a prism, cylinder, pyramid, and cone into flat patterns.]

---

### Development Examples
*   **Square Prism:** Base $30\text{ mm}$, height $50\text{ mm}$. Stretch-out line length = perimeter ($4 \times 30 = 120\text{ mm}$).
*   **Truncated Pentagonal Prism:** Base side $20\text{ mm}$, height $50\text{ mm}$. Cut by a plane at $60^\circ$ to the axis.
*   **Truncated Hexagonal Prism:** Base side $30\text{ mm}$, axis $75\text{ mm}$. Cut by a plane at $30^\circ$ to HP.
*   **Cylinder:** $\phi 25\text{ mm}$, height $40\text{ mm}$. Stretch-out line length = circumference ($\pi d \approx 78.5\text{ mm}$).
*   **Cone:** Development is a sector of a circle.
    *   Radius = Slant height ($s$).
    *   Included angle $\theta = (r/s) \times 360^\circ$.
*   **Square Pyramid:** Base $30\text{ mm}$, height $60\text{ mm}$. Requires finding the **true length** of the slant edge using the rotation method.
*   **Frustum of Square Pyramid:** Base $30\text{ mm}$, axis $40\text{ mm}$. Cut by a horizontal plane at height $20\text{ mm}$.

---

### Development Exercises
1.  **Truncated Hexagonal Pyramid:** Base side $30\text{ mm}$, height $75\text{ mm}$. Cut by a plane at $45^\circ$ to HP through the midpoint of the axis. Draw sectioned top view and lateral development.
2.  **Truncated Pentagonal Prism:** Base $45\text{ mm}$, height $80\text{ mm}$. Cut by a plane at $45^\circ$ to HP at a point $50\text{ mm}$ from the base. Construct projections, true shape of section, and development.
3.  **Truncated Cylinder:** $\phi 45\text{ mm}$, height $60\text{ mm}$. Cut by an inclined plane. Draw the development (sine-wave-like curve).

---

# Lesson 7: Curves of Intersection

### Introduction
When two solids meet, the line along which their surfaces meet is called the **curve of intersection** or **line of interpenetration**.

### Methods of Determining the Curve:
1.  **Line Method (Generator Method):** Surface of each solid is divided into lines (generators). The points where the lines of one solid intersect the lines of the other are points on the curve.
2.  **Cutting Plane Method:** Pass a series of planes through both solids. The intersection of the resulting sections of the two solids gives points on the curve.

[Visual Description: 3D models of intersecting pipes (T-joints) and a diagram (Figure 8.1) showing a horizontal cylinder penetrating a vertical one.]

---

### Procedure: Line Method (Cylinder-Cylinder)
*   **Example:** Vertical cylinder ($\phi 50$, $L70$) penetrated by a horizontal cylinder ($\phi 45$, $L80$).
*   **Step 1:** Draw projections of uncut cylinders.
*   **Step 2:** The side view of the horizontal cylinder is a circle.
*   **Step 3:** Draw generators on the horizontal cylinder.
*   **Step 4:** Locate intersection points in the side view and project them to the front view.
*   **Step 5:** Join the points with a smooth curve.

### Example 8.2: Prism-Prism Intersection
*   Vertical square prism (side $50$, axis $90$) penetrated by a horizontal square prism (side $35$, axis $90$).
*   The penetrating prism's axis is $8\text{ mm}$ in front of the vertical prism's axis and $45\text{ mm}$ above the base.
*   Since the solids are "plain" (flat-faced), the intersection consists of straight lines.

### Cutting Plane Method (Prism-Cylinder)
*   Pass horizontal cutting planes through the assembly.
*   In the top view, the section of the cylinder is a rectangle and the prism is a hexagon.
*   The points where the rectangle and hexagon intersect are projected back to the front view onto the corresponding cutting plane line.

[Visual Description: Detailed multi-view projections showing the construction lines for determining intersection curves for cylinders and prisms.]

---

**Thank You!**
FOR YOUR ATTENTION, CO-OPERATION AND KNOWLEDGE, THANK YOU CLASS ... WISH YOU THE BEST OUT THERE!

[Visual Description: Final slide featuring a group photo of the engineering class.]