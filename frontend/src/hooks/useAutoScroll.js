import { useEffect, useRef } from 'react';

function useAutoScroll(messages) {
  const scrollContentRef = useRef(null);

  // فقط زمانی که طول آرایه‌ی پیام‌ها تغییر کند (یعنی پیام جدید اضافه شده)
  useEffect(() => {
    if (scrollContentRef.current) {
      scrollContentRef.current.scrollTo({
        top: scrollContentRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [messages.length]);

  return scrollContentRef;
}

export default useAutoScroll;
