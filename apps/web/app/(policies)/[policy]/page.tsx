import { notFound } from 'next/navigation';

const policies = {
  privacy: {
    title: 'Privacy notice',
    sections: [
      ['Operator', 'Rolewisp is operated by Dhruv Pratap Singh.'],
      ['What Rolewisp stores', 'When you make an account, Rolewisp stores your email and password hash. Your profile, uploaded resume, and profile photo are available through your signed-in account.'],
      ['How your information is used', 'Your profile helps you manage job preferences and receive recommendations. Recommendations use the roles and skills you save in your profile. Rolewisp stores the photo and resume files encrypted.'],
      ['Social sign-in', 'If you choose Google, LinkedIn, or GitHub sign-in, we receive the account identifier and email information needed to create or access your account.'],
      ['Public employer postings', 'A job you publish is publicly visible with its company, description, location, and application link. Your account email, profile, photo, and resume stay private to your account.'],
      ['Storage and retention', 'Profile details, photos and resume files remain until you replace or delete them, or delete your account. Sessions expire after seven days. Verification and recovery codes expire after fifteen minutes; expired authentication records are removed by scheduled maintenance. Encrypted database backups, when enabled, have a thirty-day retention limit. Deleted information can remain in a backup until that backup expires. Public job observations and change records may remain after a listing closes.'],
      ['Managing your information', 'You can edit your profile, remove your photo or resume, and delete your account in your workspace. Review any original job site’s privacy terms before applying there.'],
    ],
  },
  cookies: {
    title: 'Cookie notice',
    sections: [
      ['Session cookie', 'Rolewisp uses a session cookie to keep you signed in. Signing out revokes the session and clears its cookie.'],
      ['Social sign-in cookie', 'When you start social sign-in, a temporary cookie helps connect the callback to the sign-in you started. It expires after ten minutes.'],
      ['Optional tracking', 'Rolewisp does not currently set analytics or advertising cookies. The original job sites you visit may use their own cookies.'],
      ['Managing cookies', 'You can clear browser cookies in your browser settings. Clearing the session cookie across this site means you will need to sign in again.'],
    ],
  },
  terms: {
    title: 'Terms of use',
    sections: [
      ['Operator', 'Rolewisp is operated by Dhruv Pratap Singh.'],
      ['Job listings', 'Rolewisp indexes openings and links to the original posting or application. Check the original site for the current status, requirements, and application instructions.'],
      ['Employer postings', 'Publish roles you are authorized to advertise and provide accurate company, role, and application details. Edit or close your postings when circumstances change.'],
      ['Service use', 'Respect access permissions and request limits. Avoid submitting malicious files, impersonating another person or organization, or using the service to collect private account information.'],
      ['Your account', 'Use your own account and upload only information you are allowed to share. Avoid uploading information belonging to another person.'],
    ],
  },
  refunds: {
    title: 'Payments and refunds',
    sections: [
      ['Operator', 'Rolewisp is operated by Dhruv Pratap Singh.'],
      ['Current availability', 'Rolewisp does not currently take payments. Plus is unavailable for purchase, and there are no Rolewisp charges to refund.'],
    ],
  },
};

export function generateStaticParams() {
  return Object.keys(policies).map((policy) => ({ policy }));
}

export default async function PolicyPage({ params }: { params: Promise<{ policy: string }> }) {
  const { policy: slug } = await params;
  if (!Object.hasOwn(policies, slug)) notFound();
  const policy = policies[slug as keyof typeof policies];
  return (
    <main className="policy-page">
      <a href="/">Rolewisp home</a>
      <h1>{policy.title}</h1>
      <p>Updated November 20, 2026</p>
      {policy.sections.map(([heading, body]) => (
        <section key={heading}>
          <h2>{heading}</h2>
          <p>{body}</p>
        </section>
      ))}
      <section>
        <h2>Contact</h2>
        <p>For support or questions about this policy, contact <a href="mailto:example@rolewisp.in">example@rolewisp.in</a>.</p>
      </section>
    </main>
  );
}
