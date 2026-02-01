import {
    Body,
    Button,
    Container,
    Head,
    Heading,
    Hr,
    Html,
    Link,
    Preview,
    Section,
    Text,
} from '@react-email/components';
import * as React from 'react';

interface BetaWelcomeEmailProps {
    name: string;
    email?: string; // Added to pre-fill survey
}

export default function BetaWelcomeEmail({ name, email = '' }: BetaWelcomeEmailProps) {
    const firstName = name.split(' ')[0];
    const surveyUrl = `https://sankoslides.com/full-survey?email=${encodeURIComponent(email)}`;

    return (
        <Html>
            <Head />
            <Preview>You're on the list! Welcome to SankoSlides Beta 🚀</Preview>
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
                            You're on the list, {firstName}! 🚀
                        </Heading>

                        <Text style={paragraph}>
                            Hey, it's Kevin from SankoSlides here.
                        </Text>
                        <Text style={paragraph}>
                            Thanks so much for joining the beta waitlist. I'm building SankoSlides to make creating academic presentations actually bearable (and maybe even fun), so having you here means a lot.
                        </Text>
                        <Text style={paragraph}>
                            We're currently rolling out access in batches to make sure everything is perfect.
                        </Text>

                        {/* Survey CTA */}
                        <Section style={highlightCard}>
                            <Heading as="h3" style={cardHeading}>
                                Want to get access sooner?
                            </Heading>
                            <Text style={cardText}>
                                Complete your beta profile to move up the priority list and unlock your "Beta Badge". It takes less than 2 minutes.
                            </Text>
                            <Button style={button} href={surveyUrl}>
                                Complete My Profile &rarr;
                            </Button>
                        </Section>

                        <Text style={paragraph}>
                            While you wait, I'd love to have you in our community. I post updates and sneak peeks there almost every day.
                        </Text>

                        {/* Community Links (Placeholders) */}
                        <Section style={linkRow}>
                            <Link href="https://twitter.com/sankoslides" style={linkButton}>
                                Follow on X / Twitter
                            </Link>
                            <Link href="https://discord.gg/placeholder" style={linkButtonSecondary}>
                                Join the Discord
                            </Link>
                        </Section>

                        <Text style={signoff}>
                            Talk soon,
                            <br />
                            Kevin
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

// Styles
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
    marginBottom: '20px',
    marginTop: '0',
};

const paragraph = {
    fontSize: '16px',
    lineHeight: '1.6',
    color: '#d4d4d8',
    marginBottom: '24px',
};

const highlightCard = {
    backgroundColor: 'rgba(16, 185, 129, 0.05)',
    borderRadius: '12px',
    border: '1px solid rgba(16, 185, 129, 0.2)',
    padding: '24px',
    marginBottom: '24px',
    textAlign: 'center' as const,
};

const cardHeading = {
    fontSize: '18px',
    fontWeight: '600',
    color: '#10b981',
    marginTop: '0',
    marginBottom: '8px',
};

const cardText = {
    fontSize: '14px',
    lineHeight: '1.5',
    color: '#d4d4d8',
    margin: '0 0 20px 0',
};

const button = {
    backgroundColor: '#10b981',
    borderRadius: '8px',
    color: '#000',
    fontSize: '14px',
    fontWeight: '600',
    textDecoration: 'none',
    textAlign: 'center' as const,
    display: 'inline-block',
    padding: '12px 24px',
};

const linkRow = {
    display: 'flex',
    gap: '16px',
    marginBottom: '24px',
};

const linkButton = {
    color: '#fafafa',
    fontSize: '14px',
    fontWeight: '500',
    textDecoration: 'underline',
    marginRight: '16px',
};

const linkButtonSecondary = {
    color: '#a1a1aa',
    fontSize: '14px',
    fontWeight: '500',
    textDecoration: 'underline',
};

const signoff = {
    fontSize: '16px',
    color: '#fafafa',
    fontWeight: '500',
    marginTop: '32px',
    marginBottom: '0',
    lineHeight: '1.6',
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

