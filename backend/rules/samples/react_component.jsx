// Test cases for rule: react-dangerously-set-inner-html

export function Comment({ body }) {
  // ruleid: react-dangerously-set-inner-html
  return <div dangerouslySetInnerHTML={{ __html: body }} />;
}

export function SafeComment({ body }) {
  // ok: react-dangerously-set-inner-html
  return <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(body) }} />;
}

export function StaticBanner() {
  // ok: react-dangerously-set-inner-html
  return <div dangerouslySetInnerHTML={{ __html: "<b>Welcome</b>" }} />;
}

export function PlainText({ body }) {
  // ok: react-dangerously-set-inner-html
  return <div>{body}</div>;
}
