import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const SESSION_COOKIE = "conexus_admin_session";

/** Public paths: keep in sync with `config.matcher` exclusions below. */
export function shouldProtectPathname(pathname: string): boolean {
  if (pathname.startsWith("/_next")) return false;
  if (pathname.startsWith("/api")) return false;
  if (pathname === "/favicon.ico") return false;
  if (pathname === "/login" || pathname.startsWith("/login/")) return false;
  return true;
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (!shouldProtectPathname(pathname)) {
    return NextResponse.next();
  }

  const session = request.cookies.get(SESSION_COOKIE)?.value;
  if (!session) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/",
    "/((?!api/|api$|_next/static|_next/image|favicon.ico|login(?:/|$)).*)",
  ],
};
