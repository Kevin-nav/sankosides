import { Resend } from 'resend';

// FROM_EMAIL is configurable via env var
// Default to Resend's onboarding domain until sankoslides.com is verified in Resend
const FROM_EMAIL = process.env.RESEND_FROM_EMAIL || 'SankoSlides Beta <onboarding@resend.dev>';

let resendClient: Resend | null = null;

function getResendClient(): Resend | null {
    if (!process.env.RESEND_API_KEY) {
        return null;
    }
    if (!resendClient) {
        resendClient = new Resend(process.env.RESEND_API_KEY);
    }
    return resendClient;
}

export async function sendBetaWelcomeEmail(name: string, email: string): Promise<boolean> {
    const resend = getResendClient();

    if (!resend) {
        console.warn('RESEND_API_KEY not configured, skipping email send');
        return false;
    }

    try {
        // Dynamic import to avoid build-time issues
        const { default: BetaWelcomeEmail } = await import('@/emails/beta-welcome');

        const { error } = await resend.emails.send({
            from: FROM_EMAIL,
            to: email,
            subject: "You're on the list! Welcome to SankoSlides Beta 🚀",
            react: BetaWelcomeEmail({ name, email }),
        });

        if (error) {
            console.error('Failed to send welcome email:', error);
            return false;
        }

        console.log(`Welcome email sent to ${email}`);
        return true;
    } catch (error) {
        console.error('Error sending welcome email:', error);
        return false;
    }
}
