export default function SiteFooter() {
  return (
    <footer>
      <div className="footer-inner">
        <div className="footer-brand">
          <span className="footer-brand-title">Rolewisp</span>
          <span>Search jobs and apply at the source.</span>
          <small>
            © 2026 <a href="https://www.linkedin.com/in/dhruvpratapsingh30/" rel="me noreferrer">Dhruv Pratap Singh</a>. All rights reserved.
          </small>
        </div>
        <nav className="footer-nav" aria-label="Policies">
          <a href="/privacy">Privacy</a>
          <a href="/cookies">Cookies</a>
          <a href="/terms">Terms</a>
          <a href="/refunds">Refunds</a>
        </nav>
      </div>
    </footer>
  );
}
