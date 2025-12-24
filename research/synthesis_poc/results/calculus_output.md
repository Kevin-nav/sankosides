# UNIVERSITY OF MINES AND TECHNOLOGY
## FACULTY OF ENGINEERING
### DEPARTMENT OF MATHEMATICAL SCIENCES

**LECTURE NOTES ON CALCULUS (EL/MC/CE/RN 166)**

**Course Instructors**
Dr Lewis Brew, Dr Eric N. Wiah, Dr Paul Boye and K. Agyarko

**June, 2022**

[Visual Description: The cover page features the crest of the University of Mines and Technology. The crest is a shield with a green border. Inside, there is a sun rising over a book at the top. Below the book are a crossed hammer and pickaxe (representing mining) and a gear (representing technology). A yellow ribbon at the bottom reads "KNOWLEDGE, TRUTH AND EXCELLENCE".]

---

# CHAPTER ONE: INTRODUCTION TO CALCULUS

## 1.0 LIMITS
In calculus and its applications, we investigate how the quantities vary, and whether they approach specific values under certain conditions. The quantities usually involve function values. The definition of derivative depends on the notion of the limit of a function. The concept of limit of a function is one of the fundamental ideas that distinguishes calculus from the areas of mathematics such as algebra, trigonometry, etc.

Let a function $f$ be defined throughout an open interval containing a real number $a$, except possibly at $a$ itself. Let consider a function value $f(x)$ which gets closer to some number $L$ when $x$ gets closer and closer to $a$ but not necessarily equal to $a$. We say that $f(x)$ approaches $L$ as $x$ approaches $a$ or $f(x)$ has the limit $L$ as $x$ approaches $a$ and represent by the notation:

$$\lim_{x \to a} f(x) = L$$

**Definition:** Let $f(x)$ be defined in an open interval about $a$ except possibly $a$ itself. We say that the limit of $f(x)$ as $x$ approaches $a$ is $L$ and denote by:

$$\lim_{x \to a} f(x) = L$$

If for every $\epsilon > 0$ there exists $\delta > 0$ such that if $0 < |x - a| < \delta$ then $|f(x) - L| < \epsilon$. The rational function $f$ defined by $f(x) = \frac{1}{x}$ has no limit as $x$ approaches 0.

**Theorem 1:** If $m, a$ and $b$ are any real numbers, then:
$$\lim_{x \to a} (mx + b) = ma + b$$

**Example:** If $f(x) = \frac{3x^2 - 8x + 3}{5x + 1}$ what is $\lim_{x \to 2} f(x)$?

**Solution:**
$$f(2) = \frac{3(2)^2 - 8(2) + 3}{5(2) + 1} = \frac{-1}{11}$$

---

## Practice problems
Find:
1. $\lim_{x \to 3} (4x^2 + 6x - 2)$
2. $\lim_{x \to 1/2} \frac{4x^2 - 6x + 3}{16x^3 + 8x - 7}$
3. $\lim_{x \to 2} \frac{2x^2 - 5x + 2}{5x^2 - 7x - 6}$
4. $\lim_{x \to 2} \frac{x^2 - 4}{x - 2}$
5. $\lim_{x \to 2} \frac{x - 2}{x^3 - 8}$
6. $\lim_{x \to 9} \frac{x - 9}{\sqrt{x} - 3}$

If $f$ is a rational function, then the limits as $x \to \infty$ or $x \to -\infty$ may be found by first dividing numerator and denominator of $f(x)$ by suitable power of $x$ and then applying the limit.

**Example:** Find $\lim_{x \to \infty} \frac{3x^2 - 9}{5x^2 + 2x - 6}$

**Solution:**
$$\lim_{x \to \infty} \frac{\frac{3x^2}{x^2} - \frac{9}{x^2}}{\frac{5x^2}{x^2} + \frac{2x}{x^2} - \frac{6}{x^2}} = \lim_{x \to \infty} \frac{3 - \frac{9}{x^2}}{5 + \frac{2}{x} - \frac{6}{x^2}} = \frac{3 - 0}{5 + 0 - 0} = 3/5$$

---

## One – Sided Limits

### i. Left-hand Limit
Let $f(x)$ be defined in an open interval. The statement $\lim_{x \to a^-} f(x) = L_1$ is the left hand limit and $x$ approaches $a$ from the left with $x < a$.

### ii. Right-hand Limit
Let $f(x)$ be defined in an open interval. The statement $\lim_{x \to a^+} f(x) = L_2$ is the right hand limit and $x$ approaches $a$ from the right with $x > a$.

**Example:** If $f(x) = \begin{cases} 5 - x & \text{for } x < 1 \\ 2x^2 + 1 & \text{for } x > 1 \end{cases}$ Find $\lim_{x \to 1^+} f(x)$ and $\lim_{x \to 1^-} f(x)$

**Solution:**
$$\lim_{x \to 1^+} f(x) = \lim_{x \to 1^+} (2x^2 + 1) = 3$$
$$\lim_{x \to 1^-} f(x) = \lim_{x \to 1^-} (5 - x) = 4$$

**Example:** If $f(x) = \frac{|x|}{x}$ show that the $\lim_{x \to 0} f(x)$ exists.

**Solution:**
If $x > 0$, then $\lim_{x \to 0^+} \frac{|x|}{x} = \frac{x}{x} = 1$
If $x < 0$, then $\lim_{x \to 0^-} \frac{|x|}{x} = \frac{-x}{x} = -1$
Since the left-hand and right-hand limits are different, it follows that the limit does not exist.

---

## Limit Laws
If $\lim_{x \to a} f(x) = L$ and $\lim_{x \to a} g(x) = M$ then:
i. $\lim_{x \to a} [f(x) + g(x)] = L + M$
ii. $\lim_{x \to a} [f(x) \cdot g(x)] = L \cdot M$
iii. $\lim_{x \to a} \left[ \frac{f(x)}{g(x)} \right] = \frac{L}{M}$ provided $M \neq 0$
iv. $\lim_{x \to a} [f(x) - g(x)] = L - M$
v. $\lim_{x \to a} [cf(x)] = cL$ for every real $c$

## Limits of Trigonometric Functions
1. $\lim_{x \to 0} \sin x = 0$
2. $\lim_{x \to 0} \cos x = 1$
3. $\lim_{x \to 0} \frac{\sin x}{x} = 1$ or $\lim_{x \to 0} \frac{x}{\sin x} = 1$

**Example:** Find $\lim_{x \to 0} \frac{\sin 7x}{3x}$

**Solution:**
$$\lim_{x \to 0} \frac{\sin 7x}{3x} = \lim_{x \to 0} \frac{1}{3} \cdot \frac{\sin 7x}{x} = \lim_{x \to 0} \frac{7}{3} \cdot \frac{\sin 7x}{7x} = \frac{7}{3} \lim_{x \to 0} \frac{\sin 7x}{7x} = \frac{7}{3} \times 1 = \frac{7}{3}$$

---

# CHAPTER TWO: DIFFERENTIATION

The process of determining the derivative of a function or how quickly or slowly a function varies as the quantity on which it depends, the argument changed is known as differentiation. Specifically, it is the procedure for obtaining an expression (numerical or algebraic) for the rate of change of the function with respect to its argument. Familiar examples of rates of change include acceleration (the rate of change of velocity) and the rate of chemical reaction (rate of change of chemical composition).

**Definition:** If a function $f(x)$ is defined over an interval $[a, b]$, then taking a point $x = x_0$ in the interval, the change in value of $f(x)$ at a different point $x = x_1$ with respect to the value at $x = x_0$ divided by the change in $x = x_1$ with respect to $x = x_0$ is called the average rate of change of the function $f(x)$ with respect to $x_0$. That is:
$$\frac{\Delta f}{\Delta x} = \frac{f(x_1) - f(x_0)}{x_1 - x_0}$$
where $\Delta f = f(x_1) - f(x_0) = f(x_0 + \Delta x) - f(x_0)$ and $\Delta x = x_1 - x_0 = (x_0 + \Delta x) - x_0$.

The exact rate of change at $x = x_0$ is given by:
$$f'(x_0) = \frac{df(x)}{dx} = \lim_{\Delta x \to 0} \left( \frac{\Delta f}{\Delta x} \right) = \lim_{\Delta x \to 0} \left[ \frac{f(x_0 + \Delta x) - f(x_0)}{\Delta x} \right]$$

---

## 2.1 DIFFERENTIATION FROM FIRST PRINCIPLE
The derivative of a function $f(x) = x^n$ where $n$ is a real number can be obtained from the first principle:
$$\frac{\Delta f}{\Delta x} = \left[ \frac{(x + \Delta x)^n - x^n}{\Delta x} \right]$$

Taking the limits, we obtain:
$$\frac{df}{dx} = \lim_{\Delta x \to 0} \left( \frac{\Delta f}{\Delta x} \right) = \lim_{\Delta x \to 0} \left[ \frac{(x + \Delta x)^n - x^n}{\Delta x} \right]$$

Using binomial expansion:
$$\frac{\Delta f}{\Delta x} = \frac{x^n + nx^{n-1}\Delta x + \frac{n(n-1)}{2!}x^{n-2}(\Delta x)^2 + \dots + (\Delta x)^n - x^n}{\Delta x}$$
$$\frac{\Delta f}{\Delta x} = nx^{n-1} + \frac{n(n-1)}{2!}x^{n-2}(\Delta x) + \dots + (\Delta x)^{n-1}$$

As $\Delta x \to 0$:
$$\frac{df}{dx} = nx^{n-1}$$

**Example:** Find from first principle the derivative with respect to $x$ of $f(x) = x^2$.

**Solution:**
$$f'(x) = \lim_{\Delta x \to 0} \left[ \frac{(x + \Delta x)^2 - x^2}{\Delta x} \right] = \lim_{\Delta x \to 0} \left[ \frac{x^2 + 2x\Delta x + (\Delta x)^2 - x^2}{\Delta x} \right]$$
$$= \lim_{\Delta x \to 0} [2x + \Delta x] = 2x$$

---

## 2.1.1 Differentiation of Products from First Principle
**Theorem:** Given the differentiable functions $f(x)$ and $g(x)$, then:
$$\frac{d}{dx}[f(x)g(x)] = g(x)\frac{df(x)}{dx} + f(x)\frac{dg(x)}{dx}$$

**Proof:** Let $h(x) = f(x)g(x)$.
$$h'(x) = \lim_{\Delta x \to 0} \left[ \frac{f(x + \Delta x)g(x + \Delta x) - f(x)g(x)}{\Delta x} \right]$$
Adding and subtracting $f(x + \Delta x)g(x)$ in the numerator:
$$= \lim_{\Delta x \to 0} \left[ f(x + \Delta x) \frac{g(x + \Delta x) - g(x)}{\Delta x} + g(x) \frac{f(x + \Delta x) - f(x)}{\Delta x} \right]$$
$$= f(x)g'(x) + g(x)f'(x)$$

---

## 2.1.2 Differentiation of Quotients from First Principle
**Theorem:** Given the differentiable functions $f(x)$ and $g(x)$ then:
$$\frac{d}{dx} \left[ \frac{f(x)}{g(x)} \right] = \frac{g(x)\frac{d}{dx}f(x) - f(x)\frac{d}{dx}g(x)}{[g(x)]^2}$$

**Example:** Find from first principle the derivative of $h(x) = \frac{5x^2 - x + 7}{x^2 + x + 1}$.

**Solution:**
Using the quotient rule formula:
$$h'(x) = \frac{(x^2 + x + 1)(10x - 1) - (5x^2 - x + 7)(2x + 1)}{(x^2 + x + 1)^2}$$
$$h'(x) = \frac{6x^2 - 4x - 8}{(x^2 + x + 1)^2}$$

---

## 2.2 CHAIN RULE
**Theorem:** If $y = f(u)$ is a composition on $u = u(x)$, then:
$$\frac{dy}{dx} = \frac{dy}{du} \times \frac{du}{dx}$$

**Example:** Given $y = 3u^2 + 1$ and $u = 4x^2 + 1$. Find $\frac{dy}{dx}$.

**Solution:**
$\frac{dy}{du} = 6u$, $\frac{du}{dx} = 8x$
$\frac{dy}{dx} = (6u)(8x) = 48xu = 48x(4x^2 + 1)$

---

## 2.3 IMPLICIT DIFFERENTIATION
When $y$ is not explicitly defined in terms of $x$ (e.g., $x^3 - 3xy + y^3 = 2$), we differentiate term by term with respect to $x$.

**Example:** Find $\frac{dy}{dx}$ if $x^3 - 3xy + y^3 = 2$.

**Solution:**
$$\frac{d}{dx}(x^3) - \frac{d}{dx}(3xy) + \frac{d}{dx}(y^3) = \frac{d}{dx}(2)$$
$$3x^2 - 3 \left[ x\frac{dy}{dx} + y \right] + 3y^2\frac{dy}{dx} = 0$$
$$3x^2 - 3x\frac{dy}{dx} - 3y + 3y^2\frac{dy}{dx} = 0$$
$$\frac{dy}{dx}(3y^2 - 3x) = 3y - 3x^2 \implies \frac{dy}{dx} = \frac{y - x^2}{y^2 - x}$$

---

## 2.4 DIFFERENTIATION OF LOGARITHMIC FUNCTIONS
In general, if $y = \ln[f(x)]$, then $\frac{dy}{dx} = \frac{f'(x)}{f(x)}$.

**Example:** If $y = \ln(5x^2 + 6x - 8x^4)$, then $\frac{dy}{dx} = \frac{10x + 6 - 32x^3}{5x^2 + 6x - 8x^4}$.

**Example:** Differentiate $y = e^x$.
**Solution:** $\ln y = x \implies \frac{1}{y}\frac{dy}{dx} = 1 \implies \frac{dy}{dx} = y = e^x$.

---

## 2.5 PARAMETRIC DIFFERENTIATION
If $x = x(t)$ and $y = y(t)$, then:
$$\frac{dy}{dx} = \frac{dy/dt}{dx/dt}$$

**Example:** $x = t^2 + t + 1$, $y = 5t$. Find $\frac{dy}{dx}$.
**Solution:** $\frac{dx}{dt} = 2t + 1$, $\frac{dy}{dt} = 5$.
$$\frac{dy}{dx} = \frac{5}{2t + 1}$$

---

## 2.7 DIFFERENTIATION OF INVERSE TRIGONOMETRIC FUNCTIONS
1. $\frac{d}{dx}[\sin^{-1} x] = \frac{1}{\sqrt{1 - x^2}}$
2. $\frac{d}{dx}[\cos^{-1} x] = -\frac{1}{\sqrt{1 - x^2}}$
3. $\frac{d}{dx}[\tan^{-1} x] = \frac{1}{1 + x^2}$

---

## 2.8 LEIBNITZ’S FORMULA FOR $N^{TH}$ DIFFERENTIATION OF A PRODUCT
If $f(x) = u(x)v(x)$, then the $n^{th}$ derivative is:
$$f^{(n)}(x) = \sum_{r=0}^{n} \binom{n}{r} u^{(n-r)}(x) v^{(r)}(x)$$

**Example:** Given $f(x) = x^4 \sin x$, find $\frac{d^2f}{dx^2}$.
**Solution:** Let $u = x^4$ and $v = \sin x$.
$$\frac{d^2f}{dx^2} = \binom{2}{0}x^4(-\sin x) + \binom{2}{1}(4x^3)(\cos x) + \binom{2}{2}(12x^2)(\sin x)$$
$$= -x^4 \sin x + 8x^3 \cos x + 12x^2 \sin x$$

---

## 2.9 STATIONARY POINTS
A stationary point occurs when $\frac{dy}{dx} = 0$.

[Visual Description: Three diagrams showing types of stationary points. 
1. A U-shaped curve with an arrow pointing to the bottom labeled "Minimum turning point".
2. An inverted U-shaped curve with an arrow pointing to the top labeled "Maximum turning point".
3. An S-shaped curve with an arrow pointing to the middle flat part labeled "Point of inflexion".]

### 2.9.2 Type of Stationary Points
Using the second derivative $\frac{d^2y}{dx^2}$:
- If $\frac{d^2y}{dx^2} > 0$, it is a **minimum**.
- If $\frac{d^2y}{dx^2} < 0$, it is a **maximum**.
- If $\frac{d^2y}{dx^2} = 0$, it could be a maximum, minimum, or point of inflexion. Use the third derivative: if $\frac{d^3y}{dx^3} \neq 0$, it is a **point of inflexion**.

---

## 2.10 POWER SERIES AND INDETERMINATE FORMS
A function $f(x)$ can be represented as a Maclaurin's Series:
$$f(x) = f(0) + xf'(0) + \frac{x^2}{2!}f''(0) + \frac{x^3}{3!}f'''(0) + \dots$$

### 2.10.1 Limiting Values – Indeterminate Forms
If $\lim_{x \to x_0} \frac{f(x)}{g(x)}$ results in $\frac{0}{0}$ or $\frac{\infty}{\infty}$, use **L'Hospital's Rule**:
$$\lim_{x \to x_0} \frac{f(x)}{g(x)} = \lim_{x \to x_0} \frac{f'(x)}{g'(x)}$$

---

## 2.11 ROLLE’S THEOREM
If $f(x)$ is continuous on $[a, b]$, differentiable on $(a, b)$, and $f(a) = f(b)$, then there exists $x^*$ in $(a, b)$ such that $f'(x^*) = 0$.

## 2.12 MEAN VALUE THEOREM
If $f(x)$ is continuous on $[a, b]$ and differentiable on $(a, b)$, then there exists $x^*$ in $(a, b)$ such that:
$$f'(x^*) = \frac{f(b) - f(a)}{b - a}$$

---

# CHAPTER THREE: INTEGRATION

Integration is the reverse process of differentiation. If $F'(x) = f(x)$, then $\int f(x) dx = F(x) + c$.

## 3.2.1 Power Rule
$$\int x^n dx = \frac{x^{n+1}}{n+1} + c, \quad n \neq -1$$

## 3.2.4 Integration of Exponential/Logarithmic
$$\int e^x dx = e^x + c$$
$$\int \ln x dx = x \ln x - x + c$$
$$\int b^x dx = \frac{b^x}{\ln b} + c$$

## 3.5 INTEGRATION BY PARTS
$$\int u dv = uv - \int v du$$

**Example:** Find $\int x^2 \ln x dx$.
**Solution:** Let $u = \ln x \implies du = \frac{1}{x} dx$; $dv = x^2 dx \implies v = \frac{x^3}{3}$.
$$\int x^2 \ln x dx = \frac{x^3}{3} \ln x - \int \frac{x^3}{3} \cdot \frac{1}{x} dx = \frac{x^3}{3} \ln x - \frac{x^3}{9} + c$$

---

## 3.8 REDUCTION FORMULA
Reduction formulas express an integral in $n$ in terms of the same integral in $(n-1)$ or $(n-2)$.

**Example:** For $I_n = \int x^n e^{ax} dx$:
$$I_n = \frac{1}{a} x^n e^{ax} - \frac{n}{a} I_{n-1}$$

**Example:** For $I_n = \int \sin^n ax dx$:
$$I_n = -\frac{1}{an} \sin^{n-1} ax \cos ax + \frac{n-1}{n} I_{n-2}$$

---

# CHAPTER FOUR: PARTIAL DIFFERENTIATION

## 4.2 PARTIAL DIFFERENTIATION FROM FIRST PRINCIPLE
For $z = f(x, y)$, the partial derivative with respect to $x$ is:
$$\frac{\partial f}{\partial x} = \lim_{\Delta x \to 0} \left[ \frac{f(x + \Delta x, y) - f(x, y)}{\Delta x} \right]$$

## 4.4 TOTAL DIFFERENTIAL
The total differential $df$ of $f(x, y)$ is:
$$df = \frac{\partial f}{\partial x} dx + \frac{\partial f}{\partial y} dy$$

## 4.6 GRADIENT, DIVERGENCE AND CURL
The vector operator del ($\nabla$) is defined as:
$$\nabla = \frac{\partial}{\partial x}\mathbf{i} + \frac{\partial}{\partial y}\mathbf{j} + \frac{\partial}{\partial z}\mathbf{k}$$

- **Gradient:** $\nabla \phi = \frac{\partial \phi}{\partial x}\mathbf{i} + \frac{\partial \phi}{\partial y}\mathbf{j} + \frac{\partial \phi}{\partial z}\mathbf{k}$
- **Divergence:** $\nabla \cdot \mathbf{A} = \frac{\partial A_1}{\partial x} + \frac{\partial A_2}{\partial y} + \frac{\partial A_3}{\partial z}$
- **Curl:** $\nabla \times \mathbf{A} = \begin{vmatrix} \mathbf{i} & \mathbf{j} & \mathbf{k} \\ \frac{\partial}{\partial x} & \frac{\partial}{\partial y} & \frac{\partial}{\partial z} \\ A_1 & A_2 & A_3 \end{vmatrix}$

---

# REFERENCE
- Bird, J. (2007), *Engineering Mathematics*, 5th edition, Elsevier Ltd.
- Kreyszig, E. (2011), *Advanced Engineering Mathematics*, 10th edition, John Wiley and Sons Inc.
- Stroud, K. A. (1995), *Engineering Mathematics*, 6th Edition, Palgrave Macmillan LTD.