import subprocess
import os
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:256"
from transformers import AutoTokenizer, EsmForProteinFolding

from transformers.models.esm.openfold_utils.protein import to_pdb, Protein as OFProtein
from transformers.models.esm.openfold_utils.feats import atom14_to_atom37

def convert_outputs_to_pdb(outputs):
    final_atom_positions = atom14_to_atom37(outputs["positions"][-1], outputs)
    outputs = {k: v.to("cpu").numpy() for k, v in outputs.items()}
    final_atom_positions = final_atom_positions.cpu().numpy()
    final_atom_mask = outputs["atom37_atom_exists"]
    pdbs = []
    for i in range(outputs["aatype"].shape[0]):
        aa = outputs["aatype"][i]
        pred_pos = final_atom_positions[i]
        mask = final_atom_mask[i]
        resid = outputs["residue_index"][i] + 1
        pred = OFProtein(
            aatype=aa,
            atom_positions=pred_pos,
            atom_mask=mask,
            residue_index=resid,
            b_factors=outputs["plddt"][i],
            chain_index=outputs["chain_index"][i] if "chain_index" in outputs else None,
        )
        pdbs.append(to_pdb(pred))
    return pdbs

tokenizer = AutoTokenizer.from_pretrained("facebook/esmfold_v1")
model = EsmForProteinFolding.from_pretrained("facebook/esmfold_v1", low_cpu_mem_usage=True)


model = model.cuda()

model.esm = model.esm.half()

import torch

torch.backends.cuda.matmul.allow_tf32 = True


model.trunk.set_chunk_size(64)




import torch
def run_example(sequnce):
    tokenized_input = tokenizer([sequnce], return_tensors="pt", add_special_tokens=False)['input_ids']

    tokenized_input = tokenized_input.cuda()
    with torch.no_grad():
        import time
        st = time.time()
        print(st)
        output = model(tokenized_input)
        pdb = convert_outputs_to_pdb(output)
        print(time.time()-st)
        filename = f'pdb-{st}'
        with open(filename,'w') as writer:
            for x in pdb:
                writer.write(x)
        plddt1 = subprocess.check_output(
            ['rafm', 'plddt-stats',
             filename]).decode().strip()
        time.sleep(0.1)

        file = open('rafm_plddt_stats.tsv', mode='r')
        all_of_it = file.read()
        file.close()

        print(all_of_it)
        res = {}
        with open(f"rafm_plddt_stats-{st}.tsv", "r") as ans:
            l = ans.readline()
            l = ans.readline()
            res['residues_in_pLDDT'] = l.split()[1]
            res['pLDDT_mean'] = l.split()[2]
            res['pLDDT_median'] = l.split()[3]
            res['pLDDT80_count'] = l.split()[4]
            res['passing'] = l.split()[-2]
        # print(output)
        # print(pdb)

example = "MDLSDIELFQAITSDDTIIINKFINERENLNFRNDFGRTPLMSAIEKKKI"