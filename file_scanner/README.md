# python libs

```shell
pip install psycopg2-binary python-magic
```

# db schema

```sql
-- public.file_inventory definition

-- Drop table

-- DROP TABLE public.file_inventory;

CREATE TABLE public.file_inventory (
	id serial4 NOT NULL,
	machine varchar(255) NULL,
	"path" text NULL,
	mime_type varchar(100) NULL,
	md5 varchar(64) NULL,
	scanned_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	"size" int8 NULL,
	deleted int2 DEFAULT 0 NULL,
	gmt_create timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	scan_duration_secs float4 DEFAULT 0 NULL,
	CONSTRAINT file_inventory_path_key UNIQUE (path),
	CONSTRAINT file_inventory_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_file_md5 ON public.file_inventory USING btree (md5);
CREATE UNIQUE INDEX idx_file_path ON public.file_inventory USING btree (path);
```