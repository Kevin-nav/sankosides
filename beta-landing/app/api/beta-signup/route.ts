import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/db';
import { betaSignups } from '@/db/schema';
import { sendBetaWelcomeEmail } from '@/lib/email';
import { eq } from 'drizzle-orm';

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();

        // Validate required fields
        if (!body.fullName || !body.email || !body.university || !body.academicLevel) {
            return NextResponse.json(
                { error: 'Missing required fields' },
                { status: 400 }
            );
        }

        // Validate email format
        if (!body.email.includes('@')) {
            return NextResponse.json(
                { error: 'Invalid email address' },
                { status: 400 }
            );
        }

        // Get IP address
        const forwardedFor = request.headers.get('x-forwarded-for');
        const ipAddress = forwardedFor?.split(',')[0] || 'unknown';

        // Insert into database
        await db.insert(betaSignups).values({
            fullName: body.fullName,
            email: body.email.toLowerCase().trim(),
            whatsapp: body.whatsapp || null,
            university: body.university,
            campus: body.campus || null,
            otherUniversity: body.otherUniversity || null,
            academicLevel: body.academicLevel,
            department: body.department || null,
            frequency: body.frequency || null,
            tools: body.tools ? JSON.stringify(body.tools) : null,
            painPoints: body.painPoints || null,
            expectations: body.expectations || null,
            referral: body.referral || null,
            ipAddress,
        });

        const email = body.email.toLowerCase().trim();
        const fullName = body.fullName;

        // Send welcome email (non-blocking for response, but update DB if successful)
        sendBetaWelcomeEmail(fullName, email)
            .then(async (emailSent) => {
                if (emailSent) {
                    // Update the record with email sent timestamp
                    try {
                        await db.update(betaSignups)
                            .set({ emailSentAt: new Date() })
                            .where(eq(betaSignups.email, email));
                        console.log(`Email sent timestamp recorded for ${email}`);
                    } catch (dbErr) {
                        console.error('Failed to update email sent timestamp:', dbErr);
                    }
                }
            })
            .catch((err) => {
                console.error('Failed to send welcome email:', err);
            });

        return NextResponse.json(
            { success: true, message: 'Successfully signed up for beta!' },
            { status: 201 }
        );
    } catch (error) {
        console.error('Beta signup error:', error);

        // Check for duplicate email
        if (error instanceof Error && error.message.includes('unique')) {
            return NextResponse.json(
                { error: 'This email is already registered for the beta' },
                { status: 409 }
            );
        }

        return NextResponse.json(
            { error: 'Something went wrong. Please try again.' },
            { status: 500 }
        );
    }
}
