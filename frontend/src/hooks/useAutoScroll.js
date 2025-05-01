import { useEffect, useRef } from 'react';

function useAutoScroll(messages) {
  const scrollContentRef = useRef(null);

  useEffect(() => {
    if (scrollContentRef.current) {
      scrollContentRef.current.scrollTo({
        top: scrollContentRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [messages]);

  return scrollContentRef;
}

export default useAutoScroll;