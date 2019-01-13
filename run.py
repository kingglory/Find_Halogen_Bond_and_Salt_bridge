from __future__ import division
import iotbx.pdb
import iotbx.cif
import scitbx
import numpy as np
import pandas as pd
import mmtbx.hydrogens.build_hydrogens
from libtbx import group_args
from libtbx import easy_run

def is_bonded(atom_1, atom_2, bps_dict):
  i12 = [atom_1.i_seq, atom_2.i_seq]
  i12.sort()
  if(not tuple(i12) in bps_dict): return False
  else: return True

def in_plain(atom1,atom2,atom3,atom4,pps_dict):
  i1234 = [atom1.i_seq,atom2.i_seq,atom3.i_seq,atom4.i_seq]
  i1234.sort()
  if (not tuple(i1234) in pps_dict):return False
  else:return True

# first step write codes to find halogen bond in one pdb file
# define a function to try finding the halogen bond pairs
def find_water(hierarchy):
  get_class = iotbx.pdb.common_residue_names_get_class
  for model in hierarchy.models():
    for chain in model.chains():
      for rg in chain.residue_groups():
        for ag in rg.atom_groups():
          if (get_class(ag.resname)=="water"):
            print  ("water here :",ag)
            return ag

def find_pi(model):
  hierarchy = model.get_hierarchy()
  get_class = iotbx.pdb.common_residue_names_get_class
  for model in hierarchy.models():
    for chain in model.chains():
      for rg in chain.residue_groups():
        for ag in rg.atom_groups():
          if (get_class(ag.resname)=="pi"):
            print  ("pi here :",ag)
            return ag

"""
1,when one halogen atoms make halogen bond when other atom,
when the distance and angle limations all fited,
the bond distance more shorter ,more possible;
2, when chooseing the third atoms to make up the angle1,
the angle1 is more near 180,more possible;
3,when chooseing the fourth atoms to make up the angle2,
the angle1 is more near 120,more possible;
4,see Figure 4 in paper "Halogen bonding(X-bonding): 
 A biological perspective"
5,theta_2 angle :Geometry of X-bonds in paper 
"Halogen bond in biological molecules"
"""

def find_halogen_bonds(model, eps = 0.15, emp_scale1 = 0.6,
                       emp_scale2 = 0.75, angle_eps = 40):
  geometry = model.get_restraints_manager()
  bond_proxies_simple, asu = geometry.geometry.get_all_bond_proxies(
                                sites_cart = model.get_sites_cart())
  bps_dict = {}
  [bps_dict.setdefault(p.i_seqs, True) for p in bond_proxies_simple]
  hierarchy = model.get_hierarchy()
  vdwr = model.get_vdw_radii()
  halogens = ["CL", "BR", "I", "F"]
  halogen_bond_pairs_atom = ["S", "O", "N","F","CL","BR","I"]
  results = []
  for a1 in hierarchy.atoms():
    e1 = a1.element.upper()
    n1 = a1.name.strip().upper()
    if(e1 in halogens):
      for a2 in hierarchy.atoms():
        e2 = a2.element.upper()
        n2 = a2.name.strip().upper()
        if(not a1.is_in_same_conformer_as(a2)): continue
        if(is_bonded(a1, a2, bps_dict)): continue
        if(a1.parent().parent().resseq ==
             a2.parent().parent().resseq): continue
        if(e2 in halogen_bond_pairs_atom):
          # O2' in 3v04.pdb file will recognized as O2* ,
          #  so replace it
          n1 = n1.replace("'","*")
          n2 = n2.replace("'","*")
          n2 = n2.replace("XT","")
          # 2yj8.pdb  vdwr can't recognize 'OXT'
          d  = a1.distance(a2)
          if(n1 not in vdwr.keys()): continue
          if(n2 not in vdwr.keys()): continue
          sum_vdwr = vdwr[n1] + vdwr[n2]
          sum_vdwr_min2 = sum_vdwr * emp_scale2
          d_x_p = d / sum_vdwr
          if(sum_vdwr_min2-eps < d < sum_vdwr+eps):
            # found HB pairs-candidates
            diff_best = 1.e+9
            result = None
            for a3 in hierarchy.atoms():
              if(not is_bonded(a1, a3, bps_dict)): continue
              # theta_1 angle in paper "Halogen bond in biological molecules"
              angle_312 = (a1.angle(a2, a3, deg=True))
              # Fig.1 in "Halogen bond in biological molecules"
              #for most cases,the angle 1 is between from 130 to 180,
              # we can search in this range
              #if find something ,done!if didn't find something .
              # searching the following range
              #from 90 to 130 degrees
              if(90 < angle_312):
                for a4 in hierarchy.atoms():
                  e4 = a4.element.upper()
                  # Fig.1 in "Halogen bond in biological molecules"
                  if(e4 in ["C", "P", "S"]):
                    if(not is_bonded(a2, a4, bps_dict)): continue
                    # theta_2 angle in "Halogen bond in biological molecules"
                    angle_214 = (a2.angle(a1, a4, deg=True))
                    if(120 - angle_eps < angle_214 < 120 + angle_eps):
                      diff = abs(120 - angle_214)
                      if(diff < diff_best):
                        diff_best = diff
                        result = group_args(
                          atom_1 = a1,
                          atom_2 = a2,
                          atom_3 = a3,
                          atom_4 = a4,
                          d_12 = d,
                          sum_vdwr = sum_vdwr,
                          d_x_p = d_x_p,
                          angle_312 = angle_312,
                          angle_214 = angle_214)
                        if(result is not None):results.append(result)
  return results


def f_halogen_bonds(model, eps = 0.15, emp_scale1 = 0.6,
                       emp_scale2 = 0.75, angle_eps = 40):
  geometry = model.get_restraints_manager()
  bond_proxies_simple, asu = geometry.geometry.get_all_bond_proxies(
    sites_cart=model.get_sites_cart())
  bps_dict = {}
  [bps_dict.setdefault(p.i_seqs, True) for p in bond_proxies_simple]
  hierarchy = model.get_hierarchy()
  vdwr = model.get_vdw_radii()
  halogens = ["CL", "BR", "I", "F"]
  halogen_bond_pairs_atom = ["S", "O", "N", "F", "CL", "BR", "I"]
  atom1s = []
  atom2s = []
  atom4s = []
  results = []
  for a in hierarchy.atoms():
    if a.element.upper() in halogens:
      atom1s.append(a)
    if a.element.upper() in halogen_bond_pairs_atom:
      atom2s.append(a)
    if a.element.upper() in ["C","P","S"]:
      atom4s.append(a)
  for a1 in atom1s:
    for a2 in atom2s:
      if (not a1.is_in_same_conformer_as(a2)): continue
      if (is_bonded(a1, a2, bps_dict)): continue
      if (a1.parent().parent().resseq ==
            a2.parent().parent().resseq): continue
      d = a1.distance(a2)
      n1 = a1.name.strip().upper()
      n2 = a2.name.strip().upper()
      if (n1 not in vdwr.keys()): continue
      if (n2 not in vdwr.keys()): continue
      sum_vdwr = vdwr[n1] + vdwr[n2]
      sum_vdwr_min2 = sum_vdwr * emp_scale2
      d_x_p = d / sum_vdwr
      if (sum_vdwr_min2 - eps < d < sum_vdwr + eps):
        diff_best = 1.e+9
        result = None
        for a3 in hierarchy.atoms():
          if (not is_bonded(a1, a3, bps_dict)): continue
          angle_312 = (a1.angle(a2, a3, deg=True))
          if (90 < angle_312):
            for a4 in atom4s:
              if (not is_bonded(a2, a4, bps_dict)): continue
              # theta_2 angle in "Halogen bond in biological molecules"
              angle_214 = (a2.angle(a1, a4, deg=True))
              if (120 - angle_eps < angle_214 < 120 + angle_eps):
                diff = abs(120 - angle_214)
                if (diff < diff_best):
                  diff_best = diff
                  result = group_args(
                    atom_1=a1,
                    atom_2=a2,
                    atom_3=a3,
                    d_12=d,
                    angle_312=angle_312,
                    angle_214=angle_214)
            if (result is not None):results.append(result)
  return results
#Second step,find salt bridge in one pdb filess

Amino_Acids = ["ARG","HIS","LYS","ASP","GLU","SER","THR",
               "ASN","GLU","CYS","SEC","GLY","PRO","ALA",
               "VAL","ILE","LEU","MET","PHE","TYR","TRP"]

def find_hydrogen_bonds(model, eps = 0.15,emp_scale = 0.75):
    geometry = model.get_restraints_manager()
    bond_proxies_simple, asu = geometry.geometry.get_all_bond_proxies(
                                     sites_cart=model.get_sites_cart())
    bps_dict = {}
    [bps_dict.setdefault(p.i_seqs, True) for p in bond_proxies_simple]
    hierarchy = model.get_hierarchy()
    vdwr = model.get_vdw_radii()
    results = []
    for a1 in hierarchy.atoms():
      n1 = a1.name.strip().upper()
      if a1.element_is_hydrogen():
        for a2 in hierarchy.atoms():
          e2 = a2.element.upper()
          n2 = a2.name.strip().upper()
          if (not a1.is_in_same_conformer_as(a2)): continue
          if (is_bonded(a1, a2, bps_dict)): continue
          dict_h_bond_lengh = {"O": 0.98, "N": 1.01, "F": 0.92}
          if e2 in dict_h_bond_lengh.keys():
            if n1 not in vdwr.keys(): continue
            if n2 not in vdwr.keys(): continue
            d_12 = a1.distance(a2)
            sum_vdwr = vdwr[n1] + vdwr[n2]
            d_x_p = d_12 / sum_vdwr
            sum_vdwr_min1 = dict_h_bond_lengh[n2[0]]
            sum_vdwr_min2 = sum_vdwr * emp_scale  # 4 line 31
            if (sum_vdwr_min2 - eps < d_12 < sum_vdwr + eps):
              # found HB pairs-candidates
              for a3 in hierarchy.atoms():
                if (not is_bonded(a1, a3, bps_dict)): continue
                angle_312 = (a1.angle(a2, a3, deg=True))
                if (90 < angle_312):
                  result = group_args(
                        atom_1 = a1,
                        atom_2 = a2,
                        atom_3 = a3,
                        d_12 = d_12,
                        sum_vdwr = sum_vdwr,
                        d_x_p = d_x_p,
                        angle_312 = angle_312)
                  if (result is not None): results.append(result)

    return results



def f_hydrogen_bonds(model, eps = 0.15,emp_scale = 0.75):
    geometry = model.get_restraints_manager()
    bond_proxies_simple, asu = geometry.geometry.get_all_bond_proxies(
                                     sites_cart=model.get_sites_cart())
    bps_dict = {}
    [bps_dict.setdefault(p.i_seqs, True) for p in bond_proxies_simple]
    hierarchy = model.get_hierarchy()
    vdwr = model.get_vdw_radii()
    atom1s = []
    atom2s = []
    results = []
    dict_h_bond_lengh = {"O": 0.98, "N": 1.01, "F": 0.92}
    for a in hierarchy.atoms():
      e = a.element.upper()
      if a.element_is_hydrogen():
        atom1s.append(a)
      if e in dict_h_bond_lengh.keys():
        atom2s.append(a)
    for a1 in atom1s:
      for a2 in atom2s:
        if (not a1.is_in_same_conformer_as(a2)): continue
        if (is_bonded(a1, a2, bps_dict)): continue
        n1 = a1.name.strip().upper()
        n2 = a2.name.strip().upper()
        if n1 not in vdwr.keys(): continue
        if n2 not in vdwr.keys(): continue
        d_12 = a1.distance(a2)
        sum_vdwr = vdwr[n1] + vdwr[n2]
        sum_vdwr_min2 = sum_vdwr * emp_scale
        if (sum_vdwr_min2 - eps < d_12 < sum_vdwr + eps):
          for a3 in hierarchy.atoms():
            if (not is_bonded(a1, a3, bps_dict)): continue
            angle_312 = (a1.angle(a2, a3, deg=True))
            if (90 < angle_312):
              result = group_args(
                atom_1=a1,
                atom_2=a2,
                atom_3=a3,
                d_12=d_12,
                angle_312=angle_312)
              if (result is not None): results.append(result)

    return results



    # in the twenty one Amino Acids,[arg,his,lys] are positive Amino Acids
#  with electrically charged side chains,the positive charged atom is N
# there are some H atoms around this N atom
# [asp,glu] are negative,the negative charged atom is O
# the N atom and the O atom will make up the iron bond,the o atom and
# one of the H atom make up the H bond
def find_salt_bridge(model, eps = 0.15,emp_scale = 0.75):
  geometry = model.get_restraints_manager()
  bond_proxies_simple, asu = geometry.geometry.get_all_bond_proxies(
                                  sites_cart=model.get_sites_cart())
  bps_dict = {}
  [bps_dict.setdefault(p.i_seqs, True) for p in bond_proxies_simple]
  hierarchy = model.get_hierarchy()
  vdwr = model.get_vdw_radii()
  results = []
  ions_bonds_paris_list = []
  positive_acide = ["ARG" , "HIS" , "LYS"]
  negative_acids = ["ASP" , "GLU"]
  H_acides = ["LYS" , "ARG" , "HIS" , "SER" , "THR" , "TYP"]
  #first find ions bonds from the first following line to ---
  for a1 in hierarchy.atoms():
    #if (a1.parent().resname in positive_acide):
    e1 = a1.element.upper()
    n1 = filter(str.isalpha, a1.name.upper())
    if e1 == "N" :
      for a2 in hierarchy.atoms():
        #if (a2.parent().resname in negative_acids):
        if (is_bonded(a1, a2, bond_proxies_simple)): continue
        if (not a1.is_in_same_conformer_as(a2)): continue
        n2 = filter(str.isalpha, a2.name.upper())
        if n1 not in vdwr.keys(): continue
        if n2 not in vdwr.keys(): continue
        d_12 = a1.distance(a2)
        sum_vdwr = vdwr[n1] + vdwr[n2]
        if ( d_12 < sum_vdwr ):
          ions_bonds_paris_list.append((a1.id_str(), a2.id_str()))
          # ---to here,now find all the ions bonds;
          #the following is to find the hydrogen bonds beside the ions bonds
          for a3 in hierarchy.atoms():
            n3 = a1.name.strip().upper()
            if a3.element_is_hydrogen():
              if a1.distance(a3) > 8:continue
              for a4 in hierarchy.atoms():
                e4 = a4.element.upper()
                n4 = a4.name.strip().upper()
                if (not a3.is_in_same_conformer_as(a4)): continue
                if (is_bonded(a3, a4, bps_dict)): continue
                dict_h_bond_lengh = {"O": 0.98, "N": 1.01, "F": 0.92}
                if e4 in dict_h_bond_lengh.keys():
                  #if the mins distance between ions atoms and hydrogen bonds paris atoms
                  #  is longer than the longest distance between saltbridge :4,
                  # it won't make up saltbridge
                  d13 = a1.distance(a3)
                  d14 = a1.distance(a4)
                  d23 = a2.distance(a3)
                  d24 = a2.distance(a4)
                  if min(d13,d14,d23,d24)< 8:
                    if n3 not in vdwr.keys(): continue
                    if n4 not in vdwr.keys(): continue
                    d_34 = a1.distance(a2)
                    sum_vdwr = vdwr[n3] + vdwr[n4]
                    d_x_p = d_12 / sum_vdwr
                    sum_vdwr_min1 = dict_h_bond_lengh[n4[0]]
                    sum_vdwr_min2 = sum_vdwr * emp_scale  # 4 line 31
                    if (sum_vdwr_min2 - eps < d_12 < sum_vdwr + eps):
                      # found HB pairs-candidates
                      for a5 in hierarchy.atoms():
                        if (not is_bonded(a1, a3, bps_dict)): continue
                        angle_534 = (a3.angle(a5, a4, deg=True))
                        if (90 < angle_534):
                          result = group_args(
                                      atom_1 = a1,
                                      atom_2 = a2,
                                      atom_3 = a3,
                                      atom_4 = a3,
                                      atom_5 = a3,
                                      d_12 = d_12,
                                      d_34 = d_34,
                                      sum_vdwr = sum_vdwr,
                                      d_x_p = d_x_p,
                                      angle_534 = angle_534)
                          if (result is not None): results.append(result)
  return results

def distance_atomToArea(atom1_xyz, atom2_xyz, atom3_xyz, atom4_xyz):
  """
  Description: The distance from atom 4 to atom 1, atom 2, atom 3
  Param atom1_xyz: row slices of data boxes, three-dimensional
  Param atom2_xyz:
  Param atom3_xyz:
  Param atom_xyz:
  Return: distance from atom to plane
  """
  #Let's assume that the X of the normal vector (x, y, z) is equal to 1.
  x = 1# X coordinates of normal vectors
  p1 = np.array(atom1_xyz)  #Conversion to Matrix
  p2 = np.array(atom2_xyz)
  p3 = np.array(atom3_xyz)
  p4 = np.array(atom4_xyz)
  v12 = p1 - p2  #Vectors from P1 to P2
  v13 = p1 - p3  #Vectors from P1 to P3
  X = np.vstack((v12, v13))
  #Merge vectors V12 and V13 into 2*3 matrices
  a = -X[:, 0] #The coefficient of a
  yz = np.matrix(X[:, 1:]).I.dot(a)
  #Multiply the inverse matrix of X by a
  y = yz[0, 0]  #Y coordinates of normal vectors
  z = yz[0, 1]  # Z coordinates of normal vectors
  n = np.array([x, y, z])
  #Normal vectors of the plane to which the first three atoms belong
  v41 = p4 - p1  #Vectors from P4 to P1
  return abs(v41.dot(n) / n.dot(n))


def define_pi_system(model,eps = 5):
  #pi_amino_acids = ["HIS","PRO","PHE","TYR","TYP"]
  geometry = model.get_restraints_manager()
  hierarchy = model.get_hierarchy()
  atoms = hierarchy.atoms()
  planes = []
  for proxy in geometry.geometry.planarity_proxies:
    planes.append(atoms.select(proxy.i_seqs))
    print [a.xyz for a in atoms.select(proxy.i_seqs)]
  print len(planes)
  STOP()




