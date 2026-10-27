DROP TABLE IF EXISTS public.prod_notification;
DROP TABLE IF EXISTS public.prod_stage_proof;

ALTER TABLE public.prod_productionorder
ADD COLUMN IF NOT EXISTS assigned_to INTEGER REFERENCES public.employee(employee_id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS public.prod_attachments (
    attachment_id SERIAL PRIMARY KEY,
    entity_type VARCHAR(30) NOT NULL DEFAULT 'stage_proof',
    order_id INTEGER REFERENCES public.prod_productionorder(order_id) ON DELETE CASCADE,
    stage_progress INTEGER,
    note VARCHAR(300),
    file_name VARCHAR(180),
    file_url TEXT,
    uploaded_by INTEGER REFERENCES public.employee(employee_id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prod_attachments_order
ON public.prod_attachments(order_id, created_at DESC);
