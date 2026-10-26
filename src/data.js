export const scenes={
 indoor:{index:'01',title:'Everyday spaces.<br/>Extraordinary possibilities.',subtitle:'A home filled with objects that open, slide, fold, and turn.'},
 outdoor:{index:'02',title:'A bigger playground.<br/>A richer world of motion.',subtitle:'From bicycles and playgrounds to aircraft and construction machines.'},
 space:{index:'03',title:'Beyond the familiar.<br/>Into new frontiers.',subtitle:'Articulated rovers, solar arrays, and instruments for other worlds.'},
 laboratory:{index:'04',title:'Built for discovery.<br/>Ready for interaction.',subtitle:'Robots, instruments, and workspaces with structure you can explore.'}
};
export const edits={
 component:{folder:'a_component_support_structure',title:'Rethink the support.',description:'Replace the support structure while retaining the tabletop and the rest of the assembly.',key:'support_structure',files:['01_original_tubular_legs','02_splayed_legs','03_side_panels','04_cross_trestles'],labels:['Tubular legs','Splayed legs','Side panels','Cross trestles'],values:['tubular_legs','splayed_legs','side_panels','cross_trestles']},
 count:{folder:'b_count_fence_panels',title:'Repeat with a rule.',description:'Change the number of linked fence panels. The generator rebuilds the repeated structure and connections.',key:'panel_count',files:['01_original_2_panels','02_3_panels','03_4_panels','04_10_panels'],labels:['2 panels','3 panels','4 panels','10 panels'],values:[2,3,4,10]},
 material:{folder:'c_material_chair_surfaces',title:'A different surface.',description:'Change the seat material on the chair-swing carousel while preserving its shape and articulated structure.',key:'seat_material',files:['01_original_oak','02_red_enamel','03_warm_white','04_brushed_silver'],labels:['Oak','Red enamel','Warm white','Brushed silver'],values:['oak','red_enamel','warm_white','brushed_silver']},
 size:{folder:'d_size_cabinet_width',title:'Dimensions that adapt.',description:'Change cabinet width. Dependent surfaces and placements are recomputed by the same generator.',key:'cabinet_width_m',files:['01_original_1.00m','02_0.78m','03_1.26m','04_1.50m'],labels:['1.00 m','0.78 m','1.26 m','1.50 m'],values:[1,.78,1.26,1.5]}
};
export const tasks={round_cabinet:'Open and close a cabinet door through coordinated two-arm manipulation.',folding_chair:'Fold the chair into its closed configuration.',double_door:'Close a pair of articulated double doors.',toaster:'Push down the toaster lever to its target position.',folding_ruler:'Straighten a multi-link folding ruler.'};
const names=['PartNet-Mobility','Infinigen-Articulated','PhysX-Mobility','Artiverse','LAM','SketchMobility','Articraft','RFW-A-400K'];
export const scaleRows=names.map((n,i)=>[n,...[
 [2347,46,5.10,59.86,.411],[8226,17,3.89,73.86,.393],[2024,45,4.89,55.09,.354],[3544,84,4.60,77.65,.372],[3217,650,3,53.59,.373],[4956,47,2.22,48.31,.324],[10787,244,3.71,82.83,.422],[402410,531,4.79,84.65,.453]
][i]]);
export const qualityRows=names.map((n,i)=>[n,...[
 [98.59,99.79,99.28,42,41.5],[99.95,80.53,69.44,93,93],[100,26.64,59.24,99.5,99],[99.97,97.04,94.05,77,77],[97.14,85.74,87.75,41.5,41],[99.03,82.3,72.03,42,42],[99.99,99.98,99.99,92,91.5],[100,100,100,100,99.5]
][i]]);
export const transferRows={
 ood:[['PM-only',.35944,.14805,.12802,.13076,.17423,.02481],['PM + Articraft',.46873,.25616,.11926,.23468,.16176,.02343],['PM + RFW-A-400K',.47630,.30082,.09660,.27985,.15065,.02403]],
 in:[['PM-only',.60262,.46364,.09552,.44339,.15760,.01253],['PM + Articraft',.71442,.62972,.05371,.60164,.10196,.00778],['PM + RFW-A-400K',.78873,.73550,.03501,.70295,.06268,.00661]]
};
