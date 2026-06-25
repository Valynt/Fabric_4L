"use client";

import { useState, useEffect, useCallback } from "react";
import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetTrigger,
  SheetClose,
} from "@/components/ui/sheet";
import { DEMO_URL } from "../config";

const navItems = [
  { label: "Product", href: "#product" },
  { label: "Workflow", href: "#workflow" },
  { label: "Use Cases", href: "#use-cases" },
  { label: "Trust", href: "#trust" },
  { label: "Resources", href: "#faq" },
];

export function LandingHeader() {
  const [scrolled, setScrolled] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const handleAnchorClick = useCallback((e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    e.preventDefault();
    const id = href.replace("#", "");
    const el = document.getElementById(id);
    if (el) {
      const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      el.scrollIntoView({ behavior: prefersReduced ? "auto" : "smooth", block: "start" });
    }
    setSheetOpen(false);
  }, []);

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 h-16 transition-all duration-300 ${
        scrolled
          ? "bg-background/80 backdrop-blur-md border-b border-border shadow-sm"
          : "bg-transparent"
      }`}
    >
      <div className="mx-auto flex h-full max-w-[1200px] items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <a
          href="/"
          className="text-lg font-semibold tracking-tight text-foreground"
        >
          ValuePact
        </a>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-1" aria-label="Main">
          {navItems.map((item) => (
            <a
              key={item.label}
              href={item.href}
              onClick={(e) => handleAnchorClick(e, item.href)}
              className="px-3 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors rounded-md hover:bg-accent"
            >
              {item.label}
            </a>
          ))}
        </nav>

        {/* Desktop CTAs */}
        <div className="hidden md:flex items-center gap-3">
          <a
            href="/sign-in"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors px-3 py-2"
          >
            Sign in
          </a>
          <Button asChild size="sm">
            <a href={DEMO_URL} target="_blank" rel="noopener noreferrer" aria-label="Book a demo (opens in new tab)">
              Book a demo
            </a>
          </Button>
        </div>

        {/* Mobile Menu */}
        <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
          <SheetTrigger asChild className="md:hidden">
            <Button variant="ghost" size="icon" aria-label="Open menu">
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="right" className="w-[280px] p-6">
            <div className="flex flex-col gap-6 mt-8">
              <nav className="flex flex-col gap-2" aria-label="Mobile main">
                {navItems.map((item) => (
                  <a
                    key={item.label}
                    href={item.href}
                    onClick={(e) => handleAnchorClick(e, item.href)}
                    className="text-left px-3 py-2.5 text-sm text-muted-foreground hover:text-foreground rounded-md hover:bg-accent transition-colors"
                  >
                    {item.label}
                  </a>
                ))}
              </nav>
              <div className="flex flex-col gap-3 pt-4 border-t border-border">
                <SheetClose asChild>
                  <a
                    href="/sign-in"
                    className="text-center text-sm text-muted-foreground hover:text-foreground px-3 py-2 rounded-md hover:bg-accent transition-colors"
                  >
                    Sign in
                  </a>
                </SheetClose>
                <Button asChild>
                  <a
                    href={DEMO_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label="Book a demo (opens in new tab)"
                  >
                    Book a demo
                  </a>
                </Button>
              </div>
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </header>
  );
}
