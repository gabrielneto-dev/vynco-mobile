---
id: CTX-RSK-20261106-medidas-de-plataforma-mudam
type: risk
title: Medidas e zonas seguras da Meta são referência e podem mudar
branch: marketing
tags: [plataforma-meta, arte]
status: active
confidence: medium
created_at: 2026-11-07
updated_at: 2026-11-07
source_ids: [CTX-SRC-20261106-relatorio-finalizacao]
revisit_at: 2027-02-01
---

# Risco: especificações da plataforma

- **Risco:** texto da arte cortado por interface do Reels/Stories, ou tamanho fora do recomendado.
- **Causa:** `contexto/CREATIVE_STANDARDS.md` e `agente/arte.py` usam medidas de referência (4:5 1080×1350; 9:16 1080×1920; zonas ~14% topo / ~35% base no Reels; ~250 px no Stories).
- **Mitigação:** o checklist da peça manda conferir na documentação vigente da Meta; revisar visualmente antes de publicar.
- **Nota:** nunca confundir 9:16 (vertical) com 16:9.
