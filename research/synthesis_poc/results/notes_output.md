# UNIVERSITY OF MINES AND TECHNOLOGY, TARKWA
## FACULTY OF ENGINEERING
## DEPARTMENT OF ELECTRICAL AND ELECTRONIC ENGINEERING

**LECTURE NOTES ON**
# INSTRUMENTS AND MEASUREMENTS (EL 172)

**Compiled by: Prof C. K. AMUZUVI**
**Course Instructor: Assoc Prof Joseph C. Attachie**

**Department of Electrical and Electronic Engineering**
**University of Mines and Technology**
**Tarkwa**
**June, 2025**

[Visual Description: Cover page of the lecture notes. It features a decorative border with the words "applied ELECTRICITY" repeated in the background. At the center is the University of Mines and Technology (UMaT) logo, which includes an open book, a sun, a gear, and crossed mining tools, with the motto "KNOWLEDGE, TRUTH AND EXCELLENCE".]

---

## Contents

**CHAPTER 1 MEASUREMENT SYSTEM AND TERMINOLOGIES** ... 1
1.1 Measurement System ... 1
1.2 Intelligent Measuring System ... 1
1.3 Performance Terminology ... 1
1.4 Sources of Errors of Measuring Instruments ... 2
1.4.1 Random Errors ... 3
1.4.2 Systematic Errors ... 5
1.5 Classification of Instruments ... 6
1.6 Basic Parts of Measuring Instruments ... 7

**CHAPTER 2 MOVING COIL/IRON INSTRUMENTS** ... 11
2.1 Permanent Magnet Moving Coil (PMMC) Instruments ... 11
2.2 Multi-Range Ammeters and Voltmeters ... 14
2.3 Moving-Iron Instruments ... 19

**CHAPTER 3 BRIDGE MEASUREMENTS** ... 24
3.1 Introduction ... 24
3.2 Wheatstone Bridge ... 24
3.3 AC Bridge ... 27
3.4 Hay Bridge ... 29
3.5 Wien Bridge ... 30

**CHAPTER 4 DYNAMOMETER AND WATTMETER** ... 32
4.1 Introduction to Wattmeters ... 32
4.2 Dynamometer Wattmeter Design ... 32
4.3 Induction Wattmeter ... 35
4.4 Power Measurement in a Single Phase Circuit ... 36
4.5 Power Measurement in a Three Phase Circuit ... 37
4.6 Three-Phase Wattmeters ... 40

**CHAPTER 5 OSCILLOSCOPE** ... 41
5.1 Introduction ... 41
5.2 Basic Construction of CRO ... 42
5.3 Cathode Ray Tube (CRT) ... 42
5.5 Measurements of the Oscilloscope ... 44
5.6 Lissajous Patterns ... 46

**CHAPTER 6 MISCELLANEOUS MEASURING INSTRUMENTS** ... 48
6.1 Thermocouples ... 48
6.2 Clamp Ammeter ... 49
6.3 The Field Mill (Electric Field Measurement) ... 50
6.4 Insulation Resistance Tester (Megger) ... 51

**REFERENCES** ... 52

---

# CHAPTER 1: MEASUREMENT SYSTEM AND TERMINOLOGIES

## 1.1 Measurement System
Generally, a measurement system consists of three elements, namely:

i) **The sensing element:** Also called the transducer, the sensing element produces a signal that is related to the quantity being measured. It takes information about the quantity being measured and converts it to a form that can be interpreted by the system by way of assigning a value to.

ii) **The signal converter:** This takes the signal from the sensing element and converts it into a suitable condition worthy of display or appropriate for use in a control system. The signal converter comprises three sub-components:
*   **A signal conditioner:** Converts the signal from the sensing element into a physical form suitable for display.
*   **A signal processor:** Improves the quality of the signal; e.g., amplifier for signal magnification.
*   **A signal transmitter:** Conveys the signal some distance to the display.

iii) **The display element:** The element on which the output from the measuring system is displayed. It takes the information from the signal converter and presents it in a format that can be appreciated by visual contact of the observer.

## 1.2 Intelligent Measuring System
Are systems that employ the services of a microprocessor or a computer; otherwise, it is called a *dumb* measuring system. With a dumb instrument, the system gives a measure of the quantity and the observer then processes and interprets the displayed data. An intelligent instrument makes the measurement, processes it, and interprets the data. Intelligent instruments can make decisions based on measurements made earlier, carry out calculations on data, manipulate information, and initiate action based on the results obtained.

**Calibration:** This is the process of putting marks on a display or checking a measuring system against a standard when a transducer is in a defined environment.

## 1.3 Performance Terminology
Terms used to describe the performance of measurement systems or elements include:

**a. Accuracy:** The extent to which a wrong reading might be obtained. *Static accuracy* is used when the quantity being measured does not change or changes very slowly. *Dynamic accuracy* comes in when the measuring quantities change swiftly. Accuracy may be quoted as plus or minus some value of the variable, e.g., an ammeter of $\pm 0.1\text{ A}$ at some particular current value or for all its readings. It can also be quoted as a percentage of the full-scale deflection (fsd) of the instruments. E.g., an ammeter of $2\% \text{ fsd}$. This means that the accuracy of the reading of the ammeter when used for any reading within the range $0-10\text{ A}$ is $\pm 2\%$ of $10\text{ A}$ (i.e., $\pm 0.2\text{ A}$).

**b. Bias:** The constant error that exists for the full range of its measurements.

**c. Discrimination:** The smallest change in the quantity being measured that will produce an observable change in the reading of the instrument.

**d. Error:** The difference between the result of the measurement and the true value of the quantity being measured.
$$Error = \text{Measured value} - \text{True value}$$

**e. Gain:** The output divided by the input.

**f. Precision:** A measure of the scatter of results obtained from measurements as a result of random errors. It describes the closeness of the agreement occurring between the results obtained for a quantity when it is measured several times under the same conditions.

**g. Range:** The limits between which readings can be made on an instrument.

**h. Reliability:** The probability that an instrument will operate to an agreed level of performance under the conditions specified for its use.

**i. Resolution:** The smallest interval measurable by the instrument.

**j. Sensitivity (S):**
$$S = \frac{\text{change in instrument scale reading}}{\text{change in the quantity being measured}}$$

**k. Stability:** The ability of the instrument to display the same reading when it is used to measure a constant quantity over a period of time or when that quantity is measured on a number of occasions.

## 1.4 Sources of Errors of Measuring Instruments
Numerous errors associated with measuring instruments can be classified into random or systematic errors. Random errors are those which can vary between successive readings of the same quantity. Systematic errors are errors which do not vary from one reading to another.

### 1.4.1 Random Errors
**Operation Errors:** These are errors associated with the operation of the instrument.
*   **Observational Errors:** Errors associated with reading the position of a pointer on a scale due to the scale and pointer not being in the same plane. This is sometimes called parallax error.
*   **Human Errors:** These include wrong choice of appropriate scale of multi-range instrument or selecting an ohm scale instead of an ampere scale.
*   **Environmental Errors:** Arise from environmental effects, such as a change in temperature, humidity, or electromagnetic interference.
*   **Stochastic Errors:** Result from stochastic processes such as noise.

**Noise:**
Electrical noise manifests itself as static. The noise present in a received radio signal is termed *external noise*. The noise introduced by the receiver is termed *internal noise*.

*   **External Noise:**
    *   **Man-made-noise:** Produced by spark-producing mechanisms such as engine ignition systems, fluorescent lights, and commutators in electric motors. This noise is "radiated" through the atmosphere (wave propagation).
    *   **Atmospheric noise:** Caused by naturally occurring disturbances in the earth's atmosphere, like lightning. Its intensity is inversely related to frequency.
    *   **Space noise:** Arrives from outer space. *Solar noise* originates from the sun; *cosmic noise* originates from other stars.

*   **Internal Noise:**
    *   **Thermal noise (Johnson noise/white noise):** Due to thermal interaction between free electrons and vibrating ions in a conductor. The power of this noise is:
        $$P_n = kT \Delta f$$
        Where $k = \text{Boltzmann's constant } (1.38 \times 10^{-23} \text{ J/K})$, $T = \text{temperature (K)}$, and $\Delta f = \text{bandwidth (Hz)}$.
    *   **Transistor noise (shot noise):** Due to the discrete-particle nature of current carriers. The equation for shot noise in a diode is:
        $$i_n = \sqrt{2qI_{dc} \Delta f}$$
        Where $q = \text{electron charge } (1.6 \times 10^{-19} \text{ C})$, $I_{dc} = \text{dc current (A)}$, and $\Delta f = \text{bandwidth (Hz)}$.

### 1.4.2 Systematic Errors
**a. Construction Errors:** Occur in the manufacturing process due to tolerances on dimensions and electrical component values.
**b. Approximation Errors:** Arise from assumptions made regarding relationships between quantities (e.g., assuming a linear relationship).
**c. Ageing Errors:** Result from deteriorating components over time.
**d. Insertion Errors:** Result from the insertion of the instrument into a particular location to measure a quantity.

[Visual Description: Figure 1.1 shows two circuit diagrams (a) and (b). 
(a) Shows an ammeter A in series with a parallel combination of a voltmeter V and a load $R_L$. The text notes that ammeter A reads current in both the voltmeter and load, while voltmeter V reads the potential difference (pd) across the load.
(b) Shows a voltmeter V in parallel with a series combination of an ammeter A and a load $R_L$. The text notes that ammeter A reads the exact current in the load, while voltmeter V reads the pd of both the ammeter and load.]

## 1.5 Classification of Instruments
Measuring instruments (MIs) can be classified as analogue or digital. Analogue instruments are usually based on motor action. Digital instruments employ analogue-to-digital converters.

### 1.5.1 Indicating Instruments
Indicate the instantaneous value of the quantity being measured (e.g., ammeters, voltmeters).

### 1.5.2 Recording Instruments
Give a continuous record of variations over time (e.g., recording voltmeters in substations).

### 1.5.3 Integrating Instruments
Measure and register the total quantity over time (e.g., watt-hour meters, energy meters).

### 1.5.4 Principles of Measurements
Common types include:
i. Permanent magnet moving coil (PMMC) - for DC.
ii. Moving iron instrument - for both DC and AC.
iii. Dynamometer instrument - for AC measurement only.

General principles of operation:
i. **Electromagnetic:** utilizes magnetic effects of electric currents.
ii. **Electrostatic:** utilizes forces between electrically-charged conductors.
iii. **Electro-thermic:** utilizes the heating effect.

## 1.6 Basic Parts of Measuring Instruments
Every measuring instrument is composed primarily of three essential parts:
i. Deflecting device
ii. Controlling device
iii. Damping device

### 1.6.1 Deflecting device
Provides a force which deflects a pointer. The deflection depends on the magnitude of the current, voltage, or power being measured.

### 1.6.2 Controlling devices
Exert a torque in the opposite sense to the deflecting torque. Equilibrium is reached when deflecting and controlling torques are equal.
i. **Gravity control:** A small weight is attached to the moving system.
ii. **Spring control:** Obtained by attaching two counter-wound phosphor bronze non-magnetic springs on the spindle.

[Visual Description: Figure 1.2 illustrates a gravity control mechanism. It shows a spindle with a pointer, balance weights, and control weights. The pointer is deflected through an angle $\theta$ from its zero position.
Figure 1.3 illustrates spring control. Diagram (a) shows the physical assembly with a graduated scale, pointer, control spring, and balance weight. Diagram (b) shows a simplified view of the spindle with two spiral springs A and B.]

### 1.6.3 Damping Devices
Required to bring the moving system to rest quickly without oscillation.
i. **Air friction:** Provided by a piston or vane in an air chamber.
ii. **Fluid friction:** Uses vanes in a damping oil.
iii. **Eddy current:** Induced currents in a metal former or disc.

[Visual Description: Diagrams showing different damping methods:
1. Air Friction Damping: Piston type (a piston moves in a curved air chamber) and Vane type (a vane moves in an air chamber). Application: Moving Iron Instrument.
2. Fluid Friction Damping: Vanes submerged in damping oil. Application: Electrostatic voltmeter.
3. Eddy Current Damping with metal disc: A disc rotates between the poles of a permanent magnet. Annotated formulas: 
   - emf induced: $e = B \times l \times v = B \times l \times \omega \times r$
   - Resistance of eddy current path: $R = \frac{\rho \times l}{w \times t}$
   - Eddy current: $i_e = \frac{e}{R}$
   - Damping force: $F_d = B \times l \times i_e$
   - Damping torque: $T_d = F_d \times r = \frac{B^2 \times r^2 \times A \times t}{k \times \rho} \times \omega = k_d \times \frac{d\theta}{dt}$
   Application: Induction-type wattmeter.
4. Eddy Current Damping with metal former: A moving coil on a metal former rotates in a magnetic field. Annotated formulas:
   - emf induced: $2e = 2 \times B \times l \times v = 2 \times B \times l \times \frac{\omega \times d}{2}$
   - Resistance: $R = \frac{\rho \times 2(l + d)}{w \times t}$
   - Damping torque: $T_d = F_d \times d = k_d \times \omega = k_d \times \frac{d\theta}{dt}$
   Application: PMMC instrument.]

---

# CHAPTER 2: MOVING COIL/IRON INSTRUMENTS

## 2.1 Permanent Magnet Moving Coil (PMMC) Instruments
Consists of a permanent magnet and a small lightweight coil wound on a rectangular soft iron core.

[Visual Description: Figure 2.1 (a) shows the basic construction of a PMMC instrument, including the permanent magnet (N and S poles), moving coil, iron core, spring, and pointer over a uniform scale. (b) shows details of the spindle, including the pivot, balance weight, and control spring.
Figure 2.2 (a) shows the skeleton of the PMMC and (b) shows a detailed cross-section of the spindle, pointer, soft-steel ring, upper/lower control springs, moving coil, permanent magnets, and core.]

### 2.1.1 Principle of Operation
**Deflecting Torque:**
If the coil is carrying a current of $i$ amps, the force on a coil side is $F = BilN$ (newton).
$$\text{Torque due to both coil sides } T_d = (2r)(BilN) = G \times i \text{ (Nm)}$$
Where $G$ is the Galvanometer constant: $G = 2rBlN = NBA \text{ (Nm/amp)}$.
($A = 2rl = \text{area of the coil}$, $N = \text{number of turns}$).

**Controlling torque:**
$$\text{Control torque } T_c = C\theta$$
Where $\theta = \text{deflection angle (rad)}$ and $C = \text{spring constant (Nm/rad)}$.

**Damping Torque:**
Provided by induced eddy currents in the metal former.
$$\text{Induced current } i = \frac{2BlNr \frac{d\theta}{dt}}{R} = \frac{G}{R} \frac{d\theta}{dt} \text{ (amps)}$$
$$\text{Opposing torque } T = Gi = G \frac{G}{R} \frac{d\theta}{dt} = \frac{G^2}{R} \frac{d\theta}{dt} \text{ (Nm)}$$

### 2.1.2 Equation of motion
The resulting motion is expressed as:
$$J \frac{d^2\theta}{dt^2} + D \frac{d\theta}{dt} + C\theta = Gi$$
Where $J$ is the moment of inertia. At steady state, $C\theta = Gi$, meaning the scale is linear.

## 2.2 Multi-Range Ammeters and Voltmeters
### 2.2.1 Multi-Range Ammeter (MRA)
Constructed by employing several shunt resistances with a rotary switch. A *make-before-break* switch is used to prevent damage.

[Visual Description: Figure 2.3 shows a shunt connected moving coil instrument. Figure 2.4 shows a multirange ammeter with a rotary switch selecting between shunts $R_{s1}, R_{s2}, R_{s3}, R_{s4}$. Figure 2.5 shows an alternative multirange ammeter arrangement (Ayrton shunt).]

**Example:** A PMMC instrument has $R_m = 100\ \Omega$ and $FSD = 500\ \mu\text{A}$. Determine $R_{sh}$ for a $5\text{ A}$ range.
**Solution:**
$$I_m = \frac{R_{sh}}{R_{sh} + R_m} I$$
$$500 \times 10^{-6} = \frac{R_{sh}}{R_{sh} + 100} \times 5 \Rightarrow R_{sh} = 0.01\ \Omega$$

### 2.2.2 Multi-Range Voltmeter (MRV)
Constructed by connecting a high resistance $R_{se}$ in series. A *break-before-make* switch is used.

[Visual Description: Figure 2.6 shows a DC voltmeter with a series resistor $R_{se}$. Figure 2.7 shows a multirange voltmeter using switched multiplier resistors $R_1, R_2, R_3$. Figure 2.8 shows a multirange voltmeter using series-connected multiplier resistors.]

**Formula:** $V = I_m(R_m + R)$

### 2.2.3 Advantages, Limitations and Sources of Errors of MRV
**Advantages:** Uniform scale, low power consumption, high accuracy, high torque-weight ratio.
**Limitations:** Suitable for DC only, high cost, magnetic strength variation over time.
**Errors:** Frictional, magnetic decay, thermo-electric, temperature.

### 2.2.4 Ammeter Sensitivity
Determined by the current required for full-scale deflection. Smaller current means greater sensitivity.

### 2.2.5 Voltmeter Sensitivity
Expressed in ohms per volt ($\Omega/\text{V}$).
$$\text{Sensitivity} = \frac{R_m + R_s}{V} = \frac{1}{I_{fsd}}$$

## 2.3 Moving-Iron Instruments
Two types: Repulsion (double iron) and Attraction (single iron).

[Visual Description: Figure 2.9 shows a Repulsion Type Moving-iron Instrument with fixed and moving cylindrical iron vanes. Figure 2.10 shows an Attractive Type Moving-iron Instrument where soft iron discs are attracted into a coil. Figure 2.11 shows a typical non-linear scale, crowded at the lower end. Figure 2.12 shows the resolution of forces ($mg \cos\theta, mg \sin\theta$) in a gravity control case.]

### 2.3.2 Torque Expressions
$$T(\text{torque}) = \frac{1}{2} I^2 \frac{dL}{d\theta} \text{ (Nm)}$$
Where $L$ is inductance.

### 2.3.3 Controlling torque
i. Spring control: $T_s = K_s \theta$
ii. Gravity control: $T_g = K_g \sin\theta$
At equilibrium for gravity control:
$$\theta = \sin^{-1} \left( \frac{K}{K_g} I^2 \right) \text{ [Note: text says } I \text{ but deflecting torque is proportional to } I^2 \text{]}$$

### 2.3.5 Shunts and Multipliers for MI instruments
For ammeters, the ratio of currents is:
$$\frac{I_{sh}}{I_m} = \sqrt{\frac{R_m^2 + (\omega L_m)^2}{R_{sh}^2 + (\omega L_{sh})^2}}$$
For voltmeters, the multiplier is:
$$m = \frac{V}{v} = \frac{\sqrt{(R_{se} + R_m)^2 + (\omega L_m)^2}}{\sqrt{R_m^2 + (\omega L_m)^2}}$$

---

# CHAPTER 3: BRIDGE MEASUREMENTS

## 3.1 Introduction
Bridge circuits employ the null method and operate on the principle of comparison.

[Visual Description: Figure 3.1 is a classification chart for Bridge Circuits. 
- DC Bridge (Resistance): Wheatstone, Kelvin, Megaohm.
- AC Bridge:
  - Inductance: Maxwell, Hay, Owen.
  - Capacitance: Schering.
  - Frequency: Wien.]

## 3.2 Wheatstone Bridge
Suitable for moderate resistance values: $1\ \Omega$ to $10\ \text{M}\Omega$.

[Visual Description: Figure 3.2 shows the Wheatstone bridge circuit with four resistors $R_1, R_2, R_3, R_4$ and a galvanometer in the center.]

**Balance condition:**
$$I_1 R_1 = I_2 R_2 \text{ and } I_3 R_3 = I_4 R_4$$
$$\frac{R_1}{R_3} = \frac{R_2}{R_4} \Rightarrow R_x = R_4 = R_3 \frac{R_2}{R_1}$$

### 3.2.1 Measurement Errors
Limiting error of known resistors using 1st order approximation:
$$R_x = R_3 \frac{R_2}{R_1} \left( 1 \pm \frac{\Delta R_1}{R_1} \pm \frac{\Delta R_2}{R_2} \pm \frac{\Delta R_3}{R_3} \right)$$

### 3.2.2 Sensitivity of Galvanometer
Using Thévenin's theorem:
$$V_{TH} = V \left( \frac{R_1}{R_1 + R_3} - \frac{R_2}{R_2 + R_4} \right)$$
$$R_{TH} = R_1 // R_3 + R_2 // R_4$$
$$I_g = \frac{V_{TH}}{R_{TH} + R_g}$$

## 3.3 AC Bridge
All four arms are considered as impedance $Z$.
**Balance point:** $Z_1 Z_4 = Z_2 Z_3$
**Polar form:** $Z_1 Z_4 (\angle \theta_1 + \angle \theta_4) = Z_2 Z_3 (\angle \theta_2 + \angle \theta_3)$

## 3.4 Hay Bridge
Used for measuring unknown inductance.
$$R_x = \frac{\omega^2 C_1^2 R_1 R_2 R_3}{1 + \omega^2 C_1^2 R_1^2}$$
$$L_x = \frac{R_2 R_3 C_1}{1 + \omega^2 C_1^2 R_1^2}$$
$$Q = \frac{1}{\omega C_1 R_1}$$

## 3.5 Wien Bridge
Used for measuring unknown capacitance or frequency.
$$\frac{C_2}{C_1} = \frac{R_2}{R_1} - \frac{R_3}{R_4}$$
$$f = \frac{1}{2\pi \sqrt{R_3 R_4 C_1 C_2}}$$

---

# CHAPTER 4: DYNAMOMETER AND WATTMETER

## 4.1 Introduction to Wattmeters
Instruments for measuring electric power. Consists of a low resistance *current coil* (fixed) and a high resistance *pressure coil* (movable).

## 4.2 Dynamometer Wattmeter Design
Similar to D’Arsonval but uses a stationary coil instead of a permanent magnet.

[Visual Description: Figure 4.1 shows a dynamometer movement connected in a circuit. Figure 4.2 shows (a) schematic and (b) circuit diagram of the arrangement with a multiplier resistor $R$ in series with the potential coil.]

### 4.2.1 Operation
*   **Connection (a):** Pressure coil on supply side. Measures power loss in current coil: $P_{ind} = P_L + I^2 R_c$.
*   **Connection (b):** Current coil on supply side. Measures power loss in pressure coil: $P_{ind} = P_L + V^2/R_p$.

## 4.3 Induction Wattmeter
Used for AC power only. Uses two separate coils to produce a rotating magnetic field.

[Visual Description: Figure 4.4 shows the arrangement of an induction wattmeter, including a shunt magnet, series magnet, copper rings, aluminum disc, and damping magnet.]

## 4.4 Power Measurement in a Single Phase Circuit
$$P = VI \cos \phi \text{ [watts]}$$
$$S = VI \text{ [volt-amperes]}$$
$$Q = VI \sin \phi \text{ [var]}$$
$$\text{Power factor } = \cos \phi = \frac{P}{S}$$

## 4.5 Power Measurement in a Three Phase Circuit
### 4.5.1 One Wattmeter Method
Used if the load is balanced. $\text{Total Power} = 3 \times \text{wattmeter reading}$.

### 4.5.2 Two Wattmeter Method
Most common method for three-wire systems.
$$W_1 = V_{RY} I_R \cos(30 + \phi) = P_1$$
$$W_2 = V_{BY} I_B \cos(30 - \phi) = P_2$$
$$\text{Total Power } W_1 + W_2 = \sqrt{3} VI \cos \phi$$
$$\tan \phi = \frac{\sqrt{3}(W_2 - W_1)}{W_2 + W_1}$$

---

# CHAPTER 5: OSCILLOSCOPE

## 5.1 Introduction
The Cathode Ray Oscilloscope (CRO) measures voltage, current, time, phase, and frequency.
**Parts:** CRT, Vertical amplifier, Horizontal amplifier, Sweep generator, Trigger circuit, Power supply.

## 5.3 Cathode Ray Tube (CRT)
The heart of the CRO.
**Basic parts:** Electron gun, focusing/accelerating elements, deflecting plates, evacuated glass envelope with phosphorescent screen.

[Visual Description: Figure 5.1 shows the block diagram of a CRO. Another Figure 5.1 shows the internal components of a CRT: heater, cathode, control grid, pre-accelerating anode, focusing anode, accelerating anode, vertical and horizontal deflection plates, and the fluorescent screen.]

## 5.5 Measurements of the Oscilloscope
### 5.5.1 Voltage Measurements
$$V_{p-p} = (\text{no. of vertical divisions}) \times (\text{volts/div})$$

### 5.5.2 Period and Frequency Measurements
$$\text{Period } T = (\text{no. of horizontal divisions for 1 cycle}) \times (\text{time/div})$$
$$F = 1/T$$

### 5.5.3 Phase Shift Measurements
$$\text{Phase difference } \theta = (\text{phase difference in divisions}) \times (\text{degrees/div})$$

## 5.6 Lissajous Patterns
Used for frequency and phase measurement.
$$\frac{F_y}{F_x} = \frac{\text{Number of positive peaks}}{\text{Number of right hand side peaks}}$$
$$\sin \theta = \frac{Y_1}{Y_2}$$
Where $Y_1$ is the y-axis intercept and $Y_2$ is the maximum vertical deflection.

---

# CHAPTER 6: MISCELLANEOUS MEASURING INSTRUMENTS

## 6.1 Thermocouples
Based on the Seebeck effect.
$$e = \alpha(\theta_1 - \theta_2) + \beta(\theta_1^2 - \theta_2^2)$$
Common types: J, K, T, E, R/S, B, N, L.

## 6.2 Clamp Ammeter
Permits current measurements on a live conductor without circuit interruption using transformer action.
$$i = \frac{I}{N}$$

## 6.3 The Field Mill (Electric Field Measurement)
Based on electrostatic induction. Types: Cylindrical and Rotating Shutter.

## 6.4 Insulation Resistance Tester (Megger)
Consists of a hand-driven DC generator and a moving coil instrument. Used to measure high insulation resistance.

---

# REFERENCES
i. Srinivas, G. N. and Narasimha, S. (2018), *Electrical and Electronic Measurements and Instrumentation*, BS Publications, India.
ii. Rajut, R. K. Er. (2015), *Electrical and Electronics Measurements and Instrumentation*, S. Chand & Company Ltd, New Delhi, India, 4th Edition.
iii. Northrop, R. B. (2014), *Introduction to Instrumentation and Measurements*, Taylor & Francis Inc, New York, USA, 3rd Edition.
iv. Malaric, R. (2014), *Instrumentation and Measurement in Electrical Engineering*, Brown Walker Press, Irvine, USA.
v. Theraja, B. L. and Theraja, A. K. (2008), *A Textbook of Electrical Technology*, 24th Edition, S. Chand & Company Ltd., India.