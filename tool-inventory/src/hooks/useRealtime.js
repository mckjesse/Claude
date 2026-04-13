import { useEffect } from 'react';
import { supabase } from '../lib/supabase';

/**
 * Subscribe to realtime changes on a Supabase table.
 * Calls `onChange` whenever an INSERT, UPDATE, or DELETE occurs.
 * The callback receives the event type and new/old record.
 */
export function useRealtime(table, onChangeCallback) {
  useEffect(() => {
    const channel = supabase
      .channel(`realtime-${table}`)
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table },
        (payload) => {
          onChangeCallback(payload.eventType, payload.new, payload.old);
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [table, onChangeCallback]);
}
