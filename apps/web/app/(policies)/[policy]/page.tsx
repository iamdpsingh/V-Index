import { notFound } from 'next/navigation';

const policies = {
  privacy: {
    title: 'Privacy notice',
    sections: [
      ['What Rolewisp stores', 'When you make an account, Rolewisp stores your email and password hash. Your profile, uploaded resume, and profile photo are available through your signed-in account.'],
      ['How your information is used', 'Your profile helps you manage job preferences and receive recommendations. Recommendations use the roles and skills you save in your profile. Rolewisp stores the photo and resume files encrypted.'],
      ['Managing your information', 'You can edit your profile, remove your photo or resume, and delete your account in your workspace. Review any original job site’s privacy terms before applying there.'],
    ],
  },
  cookies: {
    title: 'Cookie notice',
    sections: [
      ['Session cookie', 'Rolewisp uses a session cookie to keep you signed in. Signing out revokes the session and clears its cookie.'],
      ['Managing cookies', 'You can clear browser cookies in your browser settings. Clearing the session cookie across this site means you will need to sign in again.'],
    ],
  },
  terms: {
    title: 'Terms of use',
    sections: [
      ['Job listings', 'Rolewisp indexes openings and links to the original posting or application. Check the original site for the current status, requirements, and application instructions.'],
      ['Your account', 'Use your own account and upload only information you are allowed to share. Avoid uploading information belonging to another person.'],
    ],
  },
  refunds: {
    title: 'Payments and refunds',
    sections: [
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
      {policy.sections.map(([heading, body]) => (
        <section key={heading}>
          <h2>{heading}</h2>
          <p>{body}</p>
        </section>
      ))}
    </main>
  );
}
