"use client";

import { useCallback } from "react";

interface FooterLink {
  label: string;
  href: string | null;
}

interface FooterColumn {
  title: string;
  links: FooterLink[];
}

const footerColumns: FooterColumn[] = [
  {
    title: "Product",
    links: [
      { label: "Product", href: "#product" },
      { label: "Workflow", href: "#workflow" },
      { label: "Use Cases", href: "#use-cases" },
      { label: "Trust", href: "#trust" },
      { label: "Resources", href: "#faq" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "Documentation", href: null },
      { label: "Contact", href: null },
      { label: "Privacy", href: null },
      { label: "Terms", href: null },
    ],
  },
  {
    title: "Resources",
    links: [
      { label: "Blog", href: null },
      { label: "Changelog", href: null },
      { label: "Security", href: null },
    ],
  },
  {
    title: "Auth",
    links: [
      { label: "Sign in", href: "/sign-in" },
      { label: "Sign up", href: "/sign-up" },
    ],
  },
];

export function LandingFooter() {
  const handleAnchorClick = useCallback((e: React.MouseEvent<HTMLAnchorElement>, href: string | null) => {
    if (!href || !href.startsWith("#")) {
      return;
    }
    e.preventDefault();
    const id = href.replace("#", "");
    const el = document.getElementById(id);
    if (el) {
      const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      el.scrollIntoView({ behavior: prefersReduced ? "auto" : "smooth", block: "start" });
    }
  }, []);

  return (
    <footer className="border-t border-border bg-muted/30">
      <div className="mx-auto max-w-[1200px] px-4 sm:px-6 lg:px-8 py-12 md:py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {footerColumns.map((col) => (
            <div key={col.title}>
              <h4 className="text-sm font-semibold text-foreground mb-4">
                {col.title}
              </h4>
              <ul className="space-y-2.5">
                {col.links.map((link) => (
                  <li key={link.label}>
                    {link.href === null ? (
                      <span className="text-sm text-muted-foreground">{link.label}</span>
                    ) : (
                      <a
                        href={link.href}
                        onClick={(e) => handleAnchorClick(e, link.href)}
                        className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                      >
                        {link.label}
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 pt-8 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-4">
          <a
            href="/"
            className="text-sm font-semibold text-foreground tracking-tight"
          >
            ValuePact
          </a>
          <p className="text-xs text-muted-foreground">
            &copy; 2026 ValuePact. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
