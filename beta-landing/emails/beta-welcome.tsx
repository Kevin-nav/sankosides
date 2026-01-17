import {
    Body,
    Container,
    Head,
    Heading,
    Hr,
    Html,
    Img,
    Link,
    Preview,
    Section,
    Text,
} from '@react-email/components';
import * as React from 'react';

interface BetaWelcomeEmailProps {
    name: string;
}

export default function BetaWelcomeEmail({ name }: BetaWelcomeEmailProps) {
    const firstName = name.split(' ')[0];

    return (
        <Html>
            <Head />
            <Preview>Welcome to the SankoSlides beta program!</Preview>
            <Body style={main}>
                <Container style={container}>
                    {/* Header */}
                    <Section style={header}>
                        <Heading style={logoText}>
                            <span style={logoAccent}>Sanko</span>Slides
                        </Heading>
                    </Section>

                    {/* Main Content */}
                    <Section style={content}>
                        <Heading style={heading}>
                            Welcome aboard, {firstName}! 🎉
                        </Heading>

                        <Text style={paragraph}>
                            You&apos;re now part of an exclusive group of beta testers who will help shape the future of academic presentations in Ghana.
                        </Text>

                        <Section style={card}>
                            <Heading as="h3" style={cardHeading}>
                                What happens next?
                            </Heading>
                            <Text style={cardText}>
                                We&apos;re working hard to get SankoSlides ready for you. As a beta tester, you&apos;ll be among the first to:
                            </Text>
                            <ul style={list}>
                                <li style={listItem}>🚀 Get early access before the public launch</li>
                                <li style={listItem}>💬 Share feedback that directly influences features</li>
                                <li style={listItem}>🐛 Help us catch bugs and improve performance</li>
                                <li style={listItem}>🎁 Receive exclusive perks for being an early supporter</li>
                            </ul>
                        </Section>

                        <Section style={card}>
                            <Heading as="h3" style={cardHeading}>
                                How you can help
                            </Heading>
                            <Text style={cardText}>
                                When you get access, here&apos;s what we&apos;d love from you:
                            </Text>
                            <ul style={list}>
                                <li style={listItem}>Try creating presentations with different topics</li>
                                <li style={listItem}>Test the UMaT formatting features</li>
                                <li style={listItem}>Report any issues or confusing experiences</li>
                                <li style={listItem}>Share ideas for features you&apos;d love to see</li>
                            </ul>
                        </Section>

                        <Text style={paragraph}>
                            We&apos;ll send you another email when your beta access is ready. Keep an eye on your inbox!
                        </Text>

                        <Text style={signoff}>
                            — The SankoSlides Team
                        </Text>
                    </Section>

                    <Hr style={divider} />

                    {/* Footer */}
                    <Section style={footer}>
                        <Text style={footerText}>
                            Made with 💚 in Ghana
                        </Text>
                        <Text style={footerLinks}>
                            <Link href="https://sankoslides.com" style={footerLink}>
                                sankoslides.com
                            </Link>
                        </Text>
                        <Text style={footerMuted}>
                            You received this email because you signed up for the SankoSlides beta.
                        </Text>
                    </Section>
                </Container>
            </Body>
        </Html>
    );
}

// Styles matching the landing page aesthetic
const main = {
    backgroundColor: '#0a0a0f',
    fontFamily: 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
};

const container = {
    margin: '0 auto',
    padding: '40px 20px',
    maxWidth: '600px',
};

const header = {
    textAlign: 'center' as const,
    marginBottom: '32px',
};

const logoText = {
    fontSize: '28px',
    fontWeight: '700',
    color: '#fafafa',
    margin: '0',
};

const logoAccent = {
    color: '#10b981',
};

const content = {
    backgroundColor: '#18181b',
    borderRadius: '16px',
    border: '1px solid rgba(255, 255, 255, 0.05)',
    padding: '32px',
};

const heading = {
    fontSize: '24px',
    fontWeight: '700',
    color: '#fafafa',
    marginBottom: '16px',
    marginTop: '0',
};

const paragraph = {
    fontSize: '16px',
    lineHeight: '1.6',
    color: '#a1a1aa',
    marginBottom: '24px',
};

const card = {
    backgroundColor: 'rgba(16, 185, 129, 0.05)',
    borderRadius: '12px',
    border: '1px solid rgba(16, 185, 129, 0.2)',
    padding: '20px',
    marginBottom: '20px',
};

const cardHeading = {
    fontSize: '16px',
    fontWeight: '600',
    color: '#10b981',
    marginTop: '0',
    marginBottom: '12px',
};

const cardText = {
    fontSize: '14px',
    lineHeight: '1.5',
    color: '#d4d4d8',
    margin: '0 0 12px 0',
};

const list = {
    margin: '0',
    padding: '0',
    listStyle: 'none',
};

const listItem = {
    fontSize: '14px',
    lineHeight: '1.8',
    color: '#d4d4d8',
    paddingLeft: '0',
};

const signoff = {
    fontSize: '16px',
    color: '#fafafa',
    fontWeight: '500',
    marginTop: '32px',
    marginBottom: '0',
};

const divider = {
    borderColor: 'rgba(255, 255, 255, 0.1)',
    margin: '32px 0',
};

const footer = {
    textAlign: 'center' as const,
};

const footerText = {
    fontSize: '14px',
    color: '#71717a',
    marginBottom: '8px',
};

const footerLinks = {
    marginBottom: '16px',
};

const footerLink = {
    fontSize: '14px',
    color: '#10b981',
    textDecoration: 'none',
};

const footerMuted = {
    fontSize: '12px',
    color: '#52525b',
    margin: '0',
};
