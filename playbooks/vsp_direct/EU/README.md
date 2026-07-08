# VSP One Block — GAD Demo

Requires the `hitachivantara.vspone_block` collection.

```
ansible-galaxy collection install hitachivantara.vspone_block
```

## Run order

| # | Playbook | What it does |
|---|----------|--------------|
| 0 | `00_verify_vault.yml` | Confirms the encrypted vault decrypts |
| 1 | `01_create_fc_volume.yml` | 15GB vol from Pool 0 → `DC1-PROD-ESXi-100`. **Copy the printed LDEV ID into `vars/demo_vars.yml` → `primary_volume_id`** |
| 2 | `02a_create_gad_nonuniform.yml` | GAD, S-VOL only on DC2 (local access) |
| 2 | `02b_create_gad_uniform.yml` | GAD, cross paths to both arrays |
| 2 | `02c_create_gad_uniform_optimized.yml` | Uniform + ALUA (local = optimized) |
| 3 | `03_expand_gad_pair.yml` | Expand pair 15GB → 50GB |
| 4 | `04_gad_lifecycle.yml` | `--tags state\|pause\|swap\|delete` |
| 5 | `05_cleanup.yml` | `--tags cleanup` — removes pair + both volumes |

Run the three `02x` playbooks one at a time — they build the **same** pair, so delete (playbook 4, `--tags delete`) between them.

## First: the vault

```
ansible-vault create vault/storage_vars.yml     # or encrypt an existing file
ansible-vault encrypt vault/storage_vars.yml
```

Every playbook is run with `--ask-vault-pass` (or `--vault-password-file`).

## Before you run

Edit `vars/demo_vars.yml` — set the FC port IDs (`dc1_port_id`, `dc2_port_id`),
`quorum_disk_id`, pool IDs, and (after step 1) `primary_volume_id`.

Destructive tasks (pause/swap/delete/cleanup) carry the `never` tag, so they
only fire when you name the tag explicitly.
