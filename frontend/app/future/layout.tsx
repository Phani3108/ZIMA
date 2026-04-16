/**
 * Future layout — sidebar is now rendered globally by RootShell,
 * so this layout just passes children through.
 */
export default function FutureLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
