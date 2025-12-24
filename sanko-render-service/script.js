const API_URL = 'http://localhost:3001';

// =================================================================
// TEST DATA
// =================================================================

const latexTests = [
    { name: "Einstein's Mass-Energy", latex: "E = mc^2" },
    { name: "Quadratic Formula", latex: "x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}" },
    { name: "Euler's Identity", latex: "e^{i\\pi} + 1 = 0" },
    { name: "Schrödinger Equation", latex: "i\\hbar\\frac{\\partial}{\\partial t}\\Psi = \\hat{H}\\Psi" },
    { name: "Maxwell's Equations", latex: "\\nabla \\cdot \\mathbf{E} = \\frac{\\rho}{\\varepsilon_0}" },
    { name: "Fourier Transform", latex: "\\hat{f}(\\xi) = \\int_{-\\infty}^{\\infty} f(x) e^{-2\\pi i x \\xi} dx" },
    { name: "Navier-Stokes", latex: "\\rho\\left(\\frac{\\partial \\mathbf{u}}{\\partial t} + \\mathbf{u} \\cdot \\nabla \\mathbf{u}\\right) = -\\nabla p + \\mu \\nabla^2 \\mathbf{u}" },
    { name: "Binomial Theorem", latex: "(x + y)^n = \\sum_{k=0}^{n} \\binom{n}{k} x^{n-k} y^k" },
    { name: "Taylor Series", latex: "f(x) = \\sum_{n=0}^{\\infty} \\frac{f^{(n)}(a)}{n!}(x-a)^n" },
    { name: "Gaussian Integral", latex: "\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}" },
    { name: "Matrix Determinant", latex: "\\det(A) = \\begin{vmatrix} a & b \\\\ c & d \\end{vmatrix} = ad - bc" },
    { name: "Ohm's Law", latex: "V = IR" },
    { name: "Capacitor Energy", latex: "E = \\frac{1}{2}CV^2" },
    { name: "RC Time Constant", latex: "\\tau = RC" },
    { name: "Complex Impedance", latex: "Z = R + j(\\omega L - \\frac{1}{\\omega C})" },
    { name: "Transfer Function", latex: "H(s) = \\frac{Y(s)}{X(s)} = \\frac{1}{1 + sRC}" },
    { name: "Laplace Transform", latex: "\\mathcal{L}\\{f(t)\\} = \\int_0^\\infty f(t)e^{-st}dt" },
    { name: "Entropy", latex: "S = -k_B \\sum_i p_i \\ln p_i" },
    { name: "Boltzmann Distribution", latex: "P(E) = \\frac{e^{-E/k_BT}}{Z}" },
    { name: "Wave Equation", latex: "\\frac{\\partial^2 u}{\\partial t^2} = c^2 \\frac{\\partial^2 u}{\\partial x^2}" },
];

const mermaidTests = [
    {
        name: "Simple Flowchart",
        diagram: `graph TD
A[Start] --> B{Decision}
B -->|Yes| C[Action 1]
B -->|No| D[Action 2]
C --> E[End]
D --> E`
    },
    {
        name: "Circuit Block Diagram",
        diagram: `graph LR
Input[Input Signal] --> Amp[Amplifier]
Amp --> Filter[Low-Pass Filter]
Filter --> ADC[ADC]
ADC --> MCU[Microcontroller]
MCU --> DAC[DAC]
DAC --> Output[Output]`
    },
    {
        name: "State Machine",
        diagram: `stateDiagram-v2
[*] --> Idle
Idle --> Running: Start
Running --> Paused: Pause
Paused --> Running: Resume
Running --> Idle: Stop
Paused --> Idle: Stop`
    },
    {
        name: "Sequence Diagram",
        diagram: `sequenceDiagram
participant User
participant Frontend
participant Backend
participant AI
User->>Frontend: Upload Document
Frontend->>Backend: POST /generate
Backend->>AI: Process Content
AI-->>Backend: Return Slides
Backend-->>Frontend: Slide Data
Frontend-->>User: Display Preview`
    },
    {
        name: "Class Diagram",
        diagram: `classDiagram
class Agent {
+String role
+String goal
+execute()
}
class Clarifier
class Synthesizer
class Planner
Agent <|-- Clarifier
Agent <|-- Synthesizer
Agent <|-- Planner`
    },
    {
        name: "Entity Relationship",
        diagram: `erDiagram
USER ||--o{ PROJECT : creates
PROJECT ||--|{ SLIDE : contains
SLIDE ||--o{ ELEMENT : has
USER {
string id
string email
}
PROJECT {
string id
string title
}`
    },
];

const citationTests = [
    {
        name: "Journal Article (APA)",
        style: "apa",
        citation: {
            author: "Smith, John",
            year: "2023",
            title: "Deep Learning for Natural Language Processing",
            source: "Journal",
            doi: "10.1234/example.2023"
        }
    },
    {
        name: "Book (APA)",
        style: "apa",
        citation: {
            author: "Johnson, Mary",
            year: "2022",
            title: "Introduction to Machine Learning",
            source: "Book"
        }
    },
    {
        name: "Conference Paper (IEEE)",
        style: "ieee",
        citation: {
            author: "Chen, Wei",
            year: "2024",
            title: "Efficient Transformers for Edge Devices",
            source: "Journal",
            url: "https://example.com/paper"
        }
    },
    {
        name: "Multiple Authors",
        style: "apa",
        citation: {
            author: "Brown, Alice",
            year: "2023",
            title: "Collaborative Filtering in Recommendation Systems",
            source: "Journal"
        }
    },
    {
        name: "Image/Figure (APA)",
        style: "apa",
        citation: {
            author: "NASA",
            year: "2022",
            title: "James Webb Space Telescope Image of Carina Nebula",
            source: "Image",
            url: "https://www.nasa.gov/webbfirstimages",
            medium: "Digital Image"
        }
    },
    {
        name: "Website (Harvard)",
        style: "harvard1",
        citation: {
            author: "Mozilla",
            year: "2024",
            title: "MDN Web Docs: JavaScript",
            source: "Website",
            url: "https://developer.mozilla.org"
        }
    },
    {
        name: "Technical Report (IEEE)",
        style: "ieee",
        citation: {
            author: "OpenAI",
            year: "2023",
            title: "GPT-4 Technical Report",
            source: "Report",
            publisher: "OpenAI",
            url: "https://arxiv.org/abs/2303.08774"
        }
    },
    {
        name: "Patent (APA)",
        style: "apa",
        citation: {
            author: "Google LLC",
            year: "2021",
            title: "System and method for large-scale machine learning",
            source: "Patent",
            publisher: "US Patent 11,222,333"
        }
    },
];

const codeTests = [
    {
        name: "Python Function",
        language: "python",
        code: `def fibonacci(n):
"""Calculate nth Fibonacci number"""
if n <= 1:
return n
return fibonacci(n-1) + fibonacci(n-2)

# Test the function
print(fibonacci(10))  # Output: 55`
    },
    {
        name: "JavaScript Async",
        language: "javascript",
        code: `async function fetchData(url) {
try {
const response = await fetch(url);
const data = await response.json();
return data;
} catch (error) {
console.error('Error:', error);
}
}`
    },
    {
        name: "Rust Struct",
        language: "rust",
        code: `#[derive(Debug)]
struct Point {
x: f64,
y: f64,
}

impl Point {
fn distance(&self, other: &Point) -> f64 {
((self.x - other.x).powi(2) + 
 (self.y - other.y).powi(2)).sqrt()
}
}`
    },
    {
        name: "SQL Query",
        language: "sql",
        code: `SELECT 
users.name,
COUNT(orders.id) as order_count,
SUM(orders.total) as total_spent
FROM users
LEFT JOIN orders ON users.id = orders.user_id
GROUP BY users.id
HAVING order_count > 5
ORDER BY total_spent DESC;`
    },
];

const tikzTests = [
    {
        name: "RC Circuit",
        tikz: `\\begin{circuitikz}
\\draw (0,0) to[R, l=$R$] (3,0)
to[C, l=$C$] (3,-2)
-- (0,-2)
to[battery1, l=$V_{in}$] (0,0);
\\end{circuitikz}`
    },
    {
        name: "Voltage Divider",
        tikz: `\\begin{circuitikz}
\\draw (0,0) node[ground]{}
to[battery1, l=$V_{in}$] (0,3)
to[R, l=$R_1$] (3,3)
to[R, l=$R_2$] (3,0) node[ground]{};
\\draw (3,3) -- (4,3) node[right]{$V_{out}$};
\\end{circuitikz}`
    },
    {
        name: "Free Body Diagram",
        tikz: `\\begin{tikzpicture}
% Box
\\draw[fill=gray!30] (0,0) rectangle (2,1.5);
\\node at (1,0.75) {$m$};

% Forces
\\draw[->, thick, red] (1,1.5) -- (1,3) node[above]{$\\vec{N}$};
\\draw[->, thick, blue] (1,0) -- (1,-1.5) node[below]{$m\\vec{g}$};
\\draw[->, thick, green!50!black] (2,0.75) -- (4,0.75) node[right]{$\\vec{F}$};
\\draw[->, thick, orange] (0,0.75) -- (-1.5,0.75) node[left]{$\\vec{f}$};
\\end{tikzpicture}`
    },
    {
        name: "Simple Op-Amp",
        tikz: `\\begin{circuitikz}
\\draw (0,0) node[op amp](opamp){};
\\draw (opamp.+) -- ++(-1,0) node[left]{$V_+$};
\\draw (opamp.-) -- ++(-1,0) node[left]{$V_-$};
\\draw (opamp.out) -- ++(1,0) node[right]{$V_{out}$};
\\end{circuitikz}`
    },
];

// =================================================================
// RENDERING FUNCTIONS
// =================================================================

function createTestCard(type, test, index) {
    const card = document.createElement('div');
    card.className = 'test-card pending';
    card.id = `${type}-${index}`;

    let inputDisplay = '';
    if (type === 'latex') {
        inputDisplay = test.latex;
    } else if (type === 'mermaid') {
        inputDisplay = test.diagram.substring(0, 80) + '...';
    } else if (type === 'code') {
        inputDisplay = `[${test.language}] ${test.code.substring(0, 50)}...`;
    } else if (type === 'tikz') {
        inputDisplay = test.tikz.substring(0, 60) + '...';
    } else {
        inputDisplay = `${test.citation.author} (${test.citation.year}) - ${test.style.toUpperCase()}`;
    }

    card.innerHTML = `
        <div class="card-header">
            <span class="test-name">${test.name}</span>
            <span class="status-badge pending" id="${type}-status-${index}">
                <svg class="icon icon-sm"><use href="#icon-clock"></use></svg>
                Pending
            </span>
        </div>
        <div class="card-body">
            <div>
                <span class="label">Input</span>
                <div class="test-input">${escapeHtml(inputDisplay)}</div>
            </div>
            <div>
                <span class="label">Output</span>
                <div class="test-output" id="${type}-output-${index}">
                    <div style="text-align:center; color: var(--text-muted); opacity:0.6;">
                        <svg class="icon icon-lg" style="margin:0 auto 8px auto;"><use href="#icon-beaker"></use></svg>
                        <span>Ready to render</span>
                    </div>
                </div>
                <div class="error-msg" id="${type}-error-${index}"></div>
            </div>
        </div>
        <div class="card-footer">
            <span class="time-badge" id="${type}-time-${index}">-- ms</span>
        </div>
    `;

    return card;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function initializeTests() {
    const sections = [
        { id: 'latexTests', data: latexTests, type: 'latex' },
        { id: 'mermaidTests', data: mermaidTests, type: 'mermaid' },
        { id: 'citationTests', data: citationTests, type: 'citation' },
        { id: 'codeTests', data: codeTests, type: 'code' },
        { id: 'tikzTests', data: tikzTests, type: 'tikz' }
    ];

    sections.forEach(sec => {
        const container = document.getElementById(sec.id);
        sec.data.forEach((test, i) => {
            container.appendChild(createTestCard(sec.type, test, i));
        });
    });

    updateStats();
}

function updateStats() {
    const all = document.querySelectorAll('.test-card');
    const success = document.querySelectorAll('.test-card.success').length;
    const failed = document.querySelectorAll('.test-card.failed').length;
    const pending = all.length - success - failed;

    document.getElementById('successCount').textContent = success;
    document.getElementById('failedCount').textContent = failed;
    document.getElementById('pendingCount').textContent = pending;
}

function setStatus(type, index, statusName) {
    const card = document.getElementById(`${type}-${index}`);
    const badge = document.getElementById(`${type}-status-${index}`);

    // Remove all specific classes
    card.classList.remove('success', 'failed', 'pending');
    badge.classList.remove('success', 'failed', 'pending');

    // Add new class
    card.classList.add(statusName);
    badge.classList.add(statusName);

    // Update icon and text
    let iconId = '';
    let text = '';

    if (statusName === 'success') {
        iconId = '#icon-check';
        text = 'Passed';
    } else if (statusName === 'failed') {
        iconId = '#icon-x';
        text = 'Failed';
    } else {
        iconId = '#icon-clock';
        text = 'Pending';
    }

    badge.innerHTML = `<svg class="icon icon-sm"><use href="${iconId}"></use></svg> ${text}`;
}

function setLoading(type, index) {
    const output = document.getElementById(`${type}-output-${index}`);
    output.innerHTML = '<div class="spinner"></div>';
}

// =================================================================
// API RUNNERS
// =================================================================

async function runLatexTest(test, index) {
    const output = document.getElementById(`latex-output-${index}`);
    const time = document.getElementById(`latex-time-${index}`);
    const error = document.getElementById(`latex-error-${index}`);

    setLoading('latex', index);

    const start = performance.now();

    try {
        const res = await fetch(`${API_URL}/render/latex`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ latex: test.latex })
        });

        const data = await res.json();
        const elapsed = (performance.now() - start).toFixed(0);

        if (data.success && data.svg) {
            output.innerHTML = data.svg;
            setStatus('latex', index, 'success');
        } else {
            throw new Error(data.error || 'No SVG returned');
        }

        time.textContent = `${elapsed} ms`;
        error.style.display = 'none';

    } catch (err) {
        setStatus('latex', index, 'failed');
        error.textContent = err.message;
        error.style.display = 'block';
        output.innerHTML = '<span style="color: var(--text-muted); font-size: 0.9rem;">Render failed</span>';
    }

    updateStats();
}

async function runMermaidTest(test, index) {
    const output = document.getElementById(`mermaid-output-${index}`);
    const time = document.getElementById(`mermaid-time-${index}`);
    const error = document.getElementById(`mermaid-error-${index}`);

    setLoading('mermaid', index);

    const start = performance.now();

    try {
        const res = await fetch(`${API_URL}/render/mermaid`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ diagram: test.diagram })
        });

        const data = await res.json();
        const elapsed = (performance.now() - start).toFixed(0);

        if (data.success && data.svg) {
            output.innerHTML = data.svg;
            setStatus('mermaid', index, 'success');
            if (data.note) {
                error.textContent = 'Note: ' + data.note;
                error.style.display = 'block';
            } else {
                error.style.display = 'none';
            }
        } else {
            throw new Error(data.error || 'No SVG returned');
        }

        time.textContent = `${elapsed} ms`;

    } catch (err) {
        setStatus('mermaid', index, 'failed');
        error.textContent = err.message;
        error.style.display = 'block';
        output.innerHTML = '<span style="color: var(--text-muted); font-size: 0.9rem;">Render failed</span>';
    }

    updateStats();
}

async function runCitationTest(test, index) {
    const output = document.getElementById(`citation-output-${index}`);
    const time = document.getElementById(`citation-time-${index}`);
    const error = document.getElementById(`citation-error-${index}`);

    setLoading('citation', index);

    const start = performance.now();

    try {
        const res = await fetch(`${API_URL}/render/citation`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                citations: [test.citation],
                style: test.style
            })
        });

        const data = await res.json();
        const elapsed = (performance.now() - start).toFixed(0);

        if (data.success && data.citations && data.citations.length > 0) {
            const formatted = data.citations[0].formatted;
            output.innerHTML = `<span style="color: #000; font-family: serif; font-size: 1rem; text-align: left;">${escapeHtml(formatted)}</span>`;
            setStatus('citation', index, 'success');

            if (data.citations[0].fallback) {
                error.textContent = 'Warning: Used fallback formatting';
                error.style.display = 'block';
            } else {
                error.style.display = 'none';
            }
        } else {
            throw new Error(data.error || 'No citation returned');
        }

        time.textContent = `${elapsed} ms`;

    } catch (err) {
        setStatus('citation', index, 'failed');
        error.textContent = err.message;
        error.style.display = 'block';
        output.innerHTML = '<span style="color: var(--text-muted); font-size: 0.9rem;">Render failed</span>';
    }

    updateStats();
}

async function runCodeTest(test, index) {
    const output = document.getElementById(`code-output-${index}`);
    const time = document.getElementById(`code-time-${index}`);
    const error = document.getElementById(`code-error-${index}`);

    setLoading('code', index);

    const start = performance.now();

    try {
        const res = await fetch(`${API_URL}/render/code`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: test.code, language: test.language })
        });

        const data = await res.json();
        const elapsed = (performance.now() - start).toFixed(0);

        if (data.success && data.html) {
            // Remove current classes from output to reset for code
            output.classList.add('code-output');
            output.innerHTML = data.html;
            setStatus('code', index, 'success');

            if (data.fallback) {
                error.textContent = 'Warning: Used fallback rendering';
                error.style.display = 'block';
            } else {
                error.style.display = 'none';
            }
        } else {
            throw new Error(data.error || 'No HTML returned');
        }

        time.textContent = `${elapsed} ms`;

    } catch (err) {
        setStatus('code', index, 'failed');
        error.textContent = err.message;
        error.style.display = 'block';
        output.innerHTML = '<span style="color: var(--text-muted); font-size: 0.9rem;">Render failed</span>';
    }

    updateStats();
}

async function runTikzTest(test, index) {
    const output = document.getElementById(`tikz-output-${index}`);
    const time = document.getElementById(`tikz-time-${index}`);
    const error = document.getElementById(`tikz-error-${index}`);

    setLoading('tikz', index);

    const start = performance.now();

    try {
        const res = await fetch(`${API_URL}/render/tikz`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tikz: test.tikz })
        });

        const data = await res.json();
        const elapsed = (performance.now() - start).toFixed(0);

        if (data.success && data.svg) {
            output.innerHTML = data.svg;
            setStatus('tikz', index, 'success');
            error.style.display = 'none';
        } else {
            throw new Error(data.error || 'No SVG returned');
        }

        time.textContent = `${elapsed} ms`;

    } catch (err) {
        setStatus('tikz', index, 'failed');
        error.textContent = err.message;
        error.style.display = 'block';
        output.innerHTML = '<span style="color: var(--text-muted); font-size: 0.9rem;">Render failed</span>';
    }

    updateStats();
}

// =================================================================
// BATCH RUNNERS
// =================================================================

async function runAllLatex() {
    for (let i = 0; i < latexTests.length; i++) await runLatexTest(latexTests[i], i);
}

async function runAllMermaid() {
    for (let i = 0; i < mermaidTests.length; i++) await runMermaidTest(mermaidTests[i], i);
}

async function runAllCitations() {
    for (let i = 0; i < citationTests.length; i++) await runCitationTest(citationTests[i], i);
}

async function runAllCode() {
    for (let i = 0; i < codeTests.length; i++) await runCodeTest(codeTests[i], i);
}

async function runAllTikz() {
    for (let i = 0; i < tikzTests.length; i++) await runTikzTest(tikzTests[i], i);
}

// =================================================================
// EVENTS
// =================================================================

document.getElementById('runAll').addEventListener('click', async () => {
    await Promise.all([
        runAllLatex(),
        runAllMermaid(),
        runAllCitations(),
        runAllCode(),
        runAllTikz()
    ]);
});

document.getElementById('runLatex').addEventListener('click', runAllLatex);
document.getElementById('runMermaid').addEventListener('click', runAllMermaid);
document.getElementById('runCitations').addEventListener('click', runAllCitations);
document.getElementById('runCode').addEventListener('click', runAllCode);
document.getElementById('runTikz').addEventListener('click', runAllTikz);

// Initialize on Load
initializeTests();
