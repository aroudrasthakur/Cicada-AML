-- Sample wallets
INSERT INTO public.wallets (wallet_address, chain_id, first_seen, last_seen, total_in, total_out) VALUES
  ('wallet_001', 'bitcoin', '2026-04-01T08:00:00+00', '2026-04-03T20:15:00+00', 142.75, 98.20),
  ('wallet_002', 'bitcoin', '2026-04-01T09:30:00+00', '2026-04-03T21:00:00+00', 88.40, 76.10),
  ('wallet_003', 'bitcoin', '2026-04-01T11:00:00+00', '2026-04-03T18:45:00+00', 210.00, 195.50),
  ('wallet_004', 'bitcoin', '2026-04-01T12:15:00+00', '2026-04-03T22:30:00+00', 55.25, 48.90),
  ('wallet_005', 'bitcoin', '2026-04-01T14:00:00+00', '2026-04-03T19:00:00+00', 330.10, 310.75);

-- Sample transactions (amounts between 0.5 and 100 BTC, spread over 3 days)
INSERT INTO public.transactions (
  transaction_id, tx_hash, sender_wallet, receiver_wallet, amount, asset_type, chain_id, timestamp, fee, label
) VALUES
  ('tx_001', '0xabc001', 'wallet_001', 'wallet_002', 0.5, 'BTC', 'bitcoin', '2026-04-01T10:00:00+00', 0.00008, NULL),
  ('tx_002', '0xabc002', 'wallet_002', 'wallet_003', 12.25, 'BTC', 'bitcoin', '2026-04-01T15:30:00+00', 0.00012, NULL),
  ('tx_003', '0xabc003', 'wallet_003', 'wallet_004', 100, 'BTC', 'bitcoin', '2026-04-01T22:45:00+00', 0.0002, NULL),
  ('tx_004', '0xabc004', 'wallet_004', 'wallet_005', 3.75, 'BTC', 'bitcoin', '2026-04-02T06:10:00+00', 0.00009, NULL),
  ('tx_005', '0xabc005', 'wallet_005', 'wallet_001', 45.5, 'BTC', 'bitcoin', '2026-04-02T12:00:00+00', 0.00015, NULL),
  ('tx_006', '0xabc006', 'wallet_001', 'wallet_003', 7.1, 'BTC', 'bitcoin', '2026-04-02T18:20:00+00', 0.00011, NULL),
  ('tx_007', '0xabc007', 'wallet_002', 'wallet_005', 88.9, 'BTC', 'bitcoin', '2026-04-02T23:55:00+00', 0.00018, NULL),
  ('tx_008', '0xabc008', 'wallet_003', 'wallet_001', 22.0, 'BTC', 'bitcoin', '2026-04-03T08:40:00+00', 0.00013, NULL),
  ('tx_009', '0xabc009', 'wallet_004', 'wallet_002', 1.2, 'BTC', 'bitcoin', '2026-04-03T14:15:00+00', 0.00007, NULL),
  ('tx_010', '0xabc010', 'wallet_005', 'wallet_004', 66.66, 'BTC', 'bitcoin', '2026-04-03T19:50:00+00', 0.00016, NULL);

-- Edges aligned with transactions
INSERT INTO public.edges (sender_wallet, receiver_wallet, transaction_id, amount, timestamp) VALUES
  ('wallet_001', 'wallet_002', 'tx_001', 0.5, '2026-04-01T10:00:00+00'),
  ('wallet_002', 'wallet_003', 'tx_002', 12.25, '2026-04-01T15:30:00+00'),
  ('wallet_003', 'wallet_004', 'tx_003', 100, '2026-04-01T22:45:00+00'),
  ('wallet_004', 'wallet_005', 'tx_004', 3.75, '2026-04-02T06:10:00+00'),
  ('wallet_005', 'wallet_001', 'tx_005', 45.5, '2026-04-02T12:00:00+00'),
  ('wallet_001', 'wallet_003', 'tx_006', 7.1, '2026-04-02T18:20:00+00'),
  ('wallet_002', 'wallet_005', 'tx_007', 88.9, '2026-04-02T23:55:00+00'),
  ('wallet_003', 'wallet_001', 'tx_008', 22.0, '2026-04-03T08:40:00+00'),
  ('wallet_004', 'wallet_002', 'tx_009', 1.2, '2026-04-03T14:15:00+00'),
  ('wallet_005', 'wallet_004', 'tx_010', 66.66, '2026-04-03T19:50:00+00');

-- Two transaction scores with different implied risk levels
INSERT INTO public.transaction_scores (
  transaction_id, behavioral_score, behavioral_anomaly_score, graph_score, entity_score,
  temporal_score, document_score, offramp_score, meta_score, predicted_label, explanation_summary
) VALUES
  (
    'tx_001',
    0.12, 0.08, 0.15, 0.10,
    0.11, 0.05, 0.09, 0.13,
    'low_risk',
    'Small amount, routine timing, no graph anomalies.'
  ),
  (
    'tx_007',
    0.78, 0.82, 0.71, 0.65,
    0.74, 0.40, 0.69, 0.76,
    'high_risk',
    'Large transfer late in window; elevated graph and velocity signals.'
  );

-- One network case and two linked wallets
INSERT INTO public.network_cases (
  id, case_name, typology, risk_score, total_amount, start_time, end_time, explanation, graph_snapshot_path
) VALUES (
  'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  'Sample layering cluster',
  'layering',
  0.84,
  177.15,
  '2026-04-01T00:00:00+00',
  '2026-04-03T23:59:59+00',
  'Coordinated flow between two wallets over the 3-day sample window.',
  'snapshots/sample_case_aaaaaaaa.graph.json'
);

INSERT INTO public.network_case_wallets (case_id, wallet_address) VALUES
  ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'wallet_002'),
  ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'wallet_005');
