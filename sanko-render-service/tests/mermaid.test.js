/**
 * Mermaid Diagram Rendering Tests
 * Tests the /render/mermaid endpoint for various diagram types
 * 
 * Note: These tests require Chrome/Chromium to be available
 */
const { api } = require('./setup');

describe('POST /render/mermaid', () => {
    describe('Flowcharts', () => {
        it('should render simple flowchart', async () => {
            const res = await api()
                .post('/render/mermaid')
                .send({
                    diagram: `graph TD
A[Start] --> B{Decision}
B -->|Yes| C[Action 1]
B -->|No| D[Action 2]
C --> E[End]
D --> E`
                })
                .expect(200);

            expect(res.body.success).toBe(true);
            expect(res.body.svg).toContain('<svg');
            expect(res.body.svg).toContain('</svg>');
            expect(res.body.diagramType).toBe('graph');
        });

        it('should render left-to-right flowchart', async () => {
            const res = await api()
                .post('/render/mermaid')
                .send({
                    diagram: `graph LR
A[Input] --> B[Process] --> C[Output]`
                })
                .expect(200);

            expect(res.body.success).toBe(true);
        });
    });

    describe('Sequence Diagrams', () => {
        it('should render sequence diagram', async () => {
            const res = await api()
                .post('/render/mermaid')
                .send({
                    diagram: `sequenceDiagram
participant User
participant Server
User->>Server: Request
Server-->>User: Response`
                })
                .expect(200);

            expect(res.body.success).toBe(true);
            expect(res.body.diagramType).toBe('sequenceDiagram');
        });
    });

    describe('State Diagrams', () => {
        it('should render state diagram', async () => {
            const res = await api()
                .post('/render/mermaid')
                .send({
                    diagram: `stateDiagram-v2
[*] --> Idle
Idle --> Running: Start
Running --> Idle: Stop`
                })
                .expect(200);

            expect(res.body.success).toBe(true);
        });
    });

    describe('Class Diagrams', () => {
        it('should render class diagram', async () => {
            const res = await api()
                .post('/render/mermaid')
                .send({
                    diagram: `classDiagram
class Animal {
  +String name
  +move()
}
class Dog
Animal <|-- Dog`
                })
                .expect(200);

            expect(res.body.success).toBe(true);
        });
    });

    describe('ER Diagrams', () => {
        it('should render entity relationship diagram', async () => {
            const res = await api()
                .post('/render/mermaid')
                .send({
                    diagram: `erDiagram
USER ||--o{ ORDER : places
ORDER ||--|{ ITEM : contains`
                })
                .expect(200);

            expect(res.body.success).toBe(true);
        });
    });

    describe('Theme Support', () => {
        it('should support default theme', async () => {
            const res = await api()
                .post('/render/mermaid')
                .send({
                    diagram: 'graph TD\nA-->B',
                    theme: 'default'
                })
                .expect(200);

            expect(res.body.success).toBe(true);
        });

        it('should support dark theme', async () => {
            const res = await api()
                .post('/render/mermaid')
                .send({
                    diagram: 'graph TD\nA-->B',
                    theme: 'dark'
                })
                .expect(200);

            expect(res.body.success).toBe(true);
        });
    });

    describe('Error Handling', () => {
        it('should return 400 when diagram field is missing', async () => {
            const res = await api()
                .post('/render/mermaid')
                .send({})
                .expect(400);

            expect(res.body.success).toBe(false);
            expect(res.body.error).toContain('diagram');
        });

        it('should handle invalid diagram syntax', async () => {
            const res = await api()
                .post('/render/mermaid')
                .send({ diagram: 'invalid diagram syntax !!!' });

            // Should either fail gracefully or return error with placeholder
            expect(res.body).toHaveProperty('success');
        });
    });
});
