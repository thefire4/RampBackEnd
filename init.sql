USE RampCoreOs;

INSERT INTO users (
	username, 
	email, 
	password, 
	tier
)
VALUES (
	'AdminEB', 
	'edb23@njit.edu', 
	'Adminpass123', 
	'admin'
	)
	(
	'enmbue', 
	'enmanuel.bueno04@gmail.com', 
	'Testpass123', 
	'standard'
);

SELECT id INTO @admin_id
FROM users where username = 'AdminEB';

INSERT INTO projects (
	name,
	status,
	style_no,
	po_no,
	project_date,
	customer,
	season,
	fabric_yarn,
	designer,
	description
)
VALUES (
	'DW11038 MENS SNOWCREST SHIRT JAC',
	'in progress',
	'DSW11038',
	'1654',
	'2026-07-10',
	'DUCKWORTH',
	'FW26',
	'AWC 100% Wool Worn',
	'BTUSA',
	'MENS SNOWCREST SHACKET (SHIRT-JACKET)',
);

SET @project_id1 = LAST_INSERT_ID();

INSERT INTO project_users (
	project_id1, 
	user_id
)
Values (
	@project_id, 
	@AdminEB
);

INSERT INTO project_colors (
	name,
	project_id1
)
VALUES (
	'Black', 
	@project_id1
);

SET @colorway_id1 = LAST_INSERT_ID();

INSERT INTO project_colors (
        name,
        project_id1
)
VALUES (
        'Dark Olive',
        @project_id1
);

SET @colorway_id2 = LAST_INSERT_ID();

INSERT INTO project_materials (
	colorway_id,
	name,
	material,
	supplier,
	supplier_contact,
	quantity, 
	location,
	article_no,
	material_size,
	uom,
	color,
	notes
)
VALUES (
	@colorway_id1,
	'Fabrc 1',
	'AWC 100% Wool Woven', 
	'American Woolen Company', 
	NULL, 
	'Throughout', 
	'Snowcrest',
	NULL,
	NULL,
	'BLACK',
	NULL	
	),
	(
	@colorway_id2,
        'Fabrc 1',
        'AWC 100% Wool Woven',
        'American Woolen Company',
        NULL,
        'Throughout',
        'Snowcrest',
        NULL,
        NULL,
        'DARK OLIVE',
        NULL
	),
	(
	@colorway_id1,
	'Fabric 2',
	'Factory source - Lining Cotton', 
	'FACTORY',
	'FACTORY',
       	NULL, 
	'Pocket flap facing, Inner collar stand, Locker loop, cuff facings, Front Placket Facing, chest pkt and flap lining, and x2 inner hem pocket, interior binding', 
	NULL,
	NULL,
	NULL, 
	'BLACK',
	NULL
	)
	@colorway_id2,
        'Fabric 2',
        'Factory source - Lining Cotton',
        'FACTORY',
        'FACTORY',
        NULL,     
        'Pocket flap facing, Inner collar stand, Locker loop, cuff facings, Front Placket Facing, chest pkt and flap lining, and x2 inner hem pocket, interior binding',
        NULL,     
        NULL,     
        NULL,      
        'BLACK',
        NULL
	)
	(
	@colorway_id1,
	'Interfacing',
	'100% POLY DEVETEX; 105GSM',
	'FACTORY', 
	'FACTORY',
	1,
	'Collar, Collar stand, placket, cuffs, pkt flaps',
	'D1121',
	NULL,
	NULL,
	'BLACK',
	NULL
	)
	(
        @colorway_id2,
        'Interfacing',
        '100% POLY DEVETEX; 105GSM',
        'FACTORY',
        'FACTORY',
        1,
        'Collar, Collar stand, placket, cuffs, pkt flaps',
        'D1121',
        NULL,
        NULL,
        'BLACK',
        NULL
        )
	(
	@colorway_id1,
	'Thread Main',
	'Factory Source',
	'FACTORY',
	'FACTORY',
	NULL,
	'Throughout',
	'choose best for fabric and weight', 
	NULL,
	NULL,
	'DTM Body',
	NULL,
	)
	(
	@colorway_id2,
	'Thread Main',
        'Factory Source',
        'FACTORY',
        'FACTORY',
        NULL,
        'Throughout',
        'choose best for fabric and weight',
        NULL,
        NULL,
        'DTM Body',
        NULL
        )
	(	
	@colorway_id1,
	'Snap',
	'24L SW61 AN4 FINISH "DUCKWORTH" BRANDED',
	'YKK', 
	'DUCKWORTH',
	'11',
	'7- CF, 2-pkts, 2-cuffs plus 2 extra males (YKK D89 & D90)',
	'28H0000AN4Y 29H0000AN4Y 27H0000AN4Y L82T79AN4Y',
	'24',
	'LIGNE',
	'AN4 - Weathered Gray',
	NULL 
	), 
	(    
        @colorway_id2,
        'Snap',
        '24L SW61 AN4 FINISH "DUCKWORTH" BRANDED',
        'YKK',
        'DUCKWORTH',
        11,
        '7- CF, 2-pkts, 2-cuffs plus 2 extra males (YKK D89 & D90)',
        '28H0000AN4Y 29H0000AN4Y 27H0000AN4Y L82T79AN4Y',
        '24',
        'LIGNE',
        'AN4 - Weathered Gray',
        NULL
        ),
	(
	@colorway_id1,
	'Main label',
	NULL, 
	'CBF Labels',
	'DUCKWORTH',
	1,
       	'CB 3/4" below Neck Seam',
	NULL,
	'2.55" x 1.5" finished', 
	'inches',
	'White',
	NULL 
	)
	@colorway_id2,
        'Main label',
        NULL, 
        'CBF Labels',
        'DUCKWORTH',
        1, 
        'CB 3/4" below Neck Seam',      
        NULL,   
        '2.55" x 1.5" finished',
        'inches',
        'White',
        NULL 
        )
	(
	@colorway_id1,
	'Care/Content label',
	'Branded care label - Snowcrest / Sawtooth - 100% WOOL ** See separate artwork**'
	'PROGRESSIVE LABEL', 
	'DUCKWORTH',
	1,
	'Sewn into wearer''s left side seam, 3" UP from bottom hem',
	NULL, 
	'1 1/4"" wide X 2"Tall', 
	'inches',
	'White satin with black print',
	NULL
	)
	(
	@colorway_id2,
        'Care/Content label',
        'Branded care label - Snowcrest / Sawtooth - 100% WOOL ** See separate artwork**'
        'PROGRESSIVE LABEL',
        'DUCKWORTH',
        1,
        'Sewn into wearer''s left side seam, 3" UP from bottom hem',
        NULL,
        '1 1/4"" wide X 2"Tall',
        'inches',
        'White satin with black print',
        NULL
        )
	(
	@colorway_id1,
	'PO & REV Number Tag',
	'PO specific label (PO 1654) & Style Rev # (REV 2)', 
	'FACTORY', 
	'FACTORY',
	1,
	'Sewn below the care/content label (Sandwich between  care/content label and garment)', 
	NULL, 
	'"Wide X 3/4"Tall',
	'inches',
	'white with black print',
	NULL,
	)
	(
        @colorway_id2,
        'PO & REV Number Tag',
        'PO specific label (PO 1654) & Style Rev # (REV 2)',
        'FACTORY',
        'FACTORY',
        1,
        'Sewn below the care/content label (Sandwich between  care/content label and garment)',
        NULL,
        '"Wide X 3/4"Tall',
        'inches',
        'white with black print',
        NULL,
        )
	(
	@colorway_id1, 
	'Placket Label'
	'Canvas - Printed label',
	'W&W LABELS', 
	'DUCKWORTH', 
	1,
	'Top lower side of underplacket.', 
	NULL, 
	'1" x 1" finished', 
	'inches', 
	'Black with White print',
	NULL
	)
	(
        @colorway_id2,
        'Placket Label'
        'Canvas - Printed label',
        'W&W LABELS',
        'DUCKWORTH',
        1,
        'Top lower side of underplacket.',
        NULL,
        '1" x 1" finished',
        'inches',
        'Black with White print',
        NULL
        )
	(
	@colorway_id1,
	'Hang Tag', 
	'SNOWCREST specfic vellum hangtag with bulb pin', 
	'ECOENCLOSE', 
	'DUCKWORTH',
	1, 
	'Safety pin attached to wearer''s left side underarm', 
	NULL,
	'2 1/2" Wide X 4 1/8" Tall', 
	'inches',
	'kraft paper',
	NULL, 
	)
	(
        @colorway_id2,
        'Hang Tag',
        'SNOWCREST specfic vellum hangtag with bulb pin',
        'ECOENCLOSE',
        'DUCKWORTH',
        1,
        'Safety pin attached to wearer''s left side underarm',
        NULL,
        '2 1/2" Wide X 4 1/8" Tall',
        'inches',
	'kraft paper',
        NULL,
        )
	(
        @colorway_id1,
        'Polybag',
	'White Glassine Bag w/ DUCKWORTH Logo Branding', 
	'ECOENCLOSE', 
	'DUCKWORTH', 
	1,
	'Over garment', 
	'GB15.75x23.5-25-CUST', 
	'15 3/4" x 23 1/2"',
	'inches', 
	'White Translucent',
	NULL
	)
	(
        @colorway_id2,
        'Polybag',
        'White Glassine Bag w/ DUCKWORTH Logo Branding',
        'ECOENCLOSE',
        'DUCKWORTH',
        1,
        'Over garment',
        'GB15.75x23.5-25-CUST',
        '15 3/4" x 23 1/2"',
        'inches',
	'White Translucent',
        NULL
        )
	(
	@colorway_id1, 
	'UPC Sticker', 
	'Barcode sticker',
	'PROGRESSIVE LABEL',
	'DUCKWORTH', 
	1, 
	'1 at back side of main hangtag', 
	NULL,
	NULL, 
	NULL,
	'white with black print',
	NULL,
	)
	(
        @colorway_id2,
        'UPC Sticker',
        'Barcode sticker',
        'PROGRESSIVE LABEL',
        'DUCKWORTH',
        1,
        '1 at back side of main hangtag',
        NULL,
        NULL,
        NULL,
        'white with black print',
        NULL,
        )
	(
	@colorway_id1,
	'SKU Number', 
	NULL, 
	NULL, 
	NULL,
	NULL, 
	NULL,
	NULL,
	NULL,
	NULL,
	'DW11038-01',
	NULL
	)
	(
        @colorway_id2,
        'SKU Number',
        NULL,
        NULL,
        NULL,
        NULL,
      	NULL,
        NULL,
        NULL,
        NULL,
        'DW11038-19',
        NULL
);

INSERT INTO points_measured (
	project_id,
	code,
	name,
	tol,
	sizes,
	measure,
	grade,
	notes, 
)
VALUES 

(@project_id1, 'A1', 'Front Length (from high point shoulder - HPS - to BTM)', '1/2', 'S', '28 1/2', '1', NULL),
(@project_id1, 'A1', 'Front Length (from high point shoulder - HPS - to BTM)', '1/2', 'M', '29 1/2', '1', NULL),
(@project_id1, 'A1', 'Front Length (from high point shoulder - HPS - to BTM)', '1/2', 'L', '30 1/2', '1', NULL),
(@project_id1, 'A1', 'Front Length (from high point shoulder - HPS - to BTM)', '1/2', 'XL', '31 1/2', '1', NULL),
(@project_id1, 'A1', 'Front Length (from high point shoulder - HPS - to BTM)', '1/2', 'XXL', '32 1/2', '1', NULL),

(@project_id1, 'A-2', 'Back length (from high point shoulder - HPS - to BTM)', '1/2', 'S', '28 1/2', '1', NULL),
(@project_id1, 'A-2', 'Back length (from high point shoulder - HPS - to BTM)', '1/2', 'M', '29 1/2', '1', NULL),
(@project_id1, 'A-2', 'Back length (from high point shoulder - HPS - to BTM)', '1/2', 'L', '30 1/2', '1', NULL),
(@project_id1, 'A-2', 'Back length (from high point shoulder - HPS - to BTM)', '1/2', 'XL', '31 1/2', '1', NULL),
(@project_id1, 'A-2', 'Back length (from high point shoulder - HPS - to BTM)', '1/2', 'XXL', '32 1/2', '1', NULL),

(@project_id1, 'B', 'Chest Width (1" under armhole)', '3/8', 'S', '21', '1 1/2', 'Add .5 XXL'),
(@project_id1, 'B', 'Chest Width (1" under armhole)', '3/8', 'M', '22 1/2', '1 1/2', 'Add .5 XXL'),
(@project_id1, 'B', 'Chest Width (1" under armhole)', '3/8', 'L', '24', '1 1/2', 'Add .5 XXL'),
(@project_id1, 'B', 'Chest Width (1" under armhole)', '3/8', 'XL', '25 1/2', '1 1/2', 'Add .5 XXL'),
(@project_id1, 'B', 'Chest Width (1" under armhole)', '3/8', 'XXL', '27 1/2', '1 1/2', 'Add .5 XXL'),

(@project_id1, 'C', 'Waist Width 18" below HPS', '3/8', 'S', '20 1/2', '1 1/2', 'Add .5 XXL'),
(@project_id1, 'C', 'Waist Width 18" below HPS', '3/8', 'M', '22', '1 1/2', 'Add .5 XXL'),
(@project_id1, 'C', 'Waist Width 18" below HPS', '3/8', 'L', '23 1/2', '1 1/2', 'Add .5 XXL'),
(@project_id1, 'C', 'Waist Width 18" below HPS', '3/8', 'XL', '25', '1 1/2', 'Add .5 XXL'),
(@project_id1, 'C', 'Waist Width 18" below HPS', '3/8', 'XXL', '27', '1 1/2', 'Add .5 XXL'),

(@project_id1, 'D', 'Bottom/Sweep - straight', '3/8', 'S', '21', '1 1/2', 'Add .5 XXL'),
(@project_id1, 'D', 'Bottom/Sweep - straight', '3/8', 'M', '22 1/2', '1 1/2', 'Add .5 XXL'),
(@project_id1, 'D', 'Bottom/Sweep - straight', '3/8', 'L', '24', '1 1/2', 'Add .5 XXL'),
(@project_id1, 'D', 'Bottom/Sweep - straight', '3/8', 'XL', '25 1/2', '1 1/2', 'Add .5 XXL'),
(@project_id1, 'D', 'Bottom/Sweep - straight', '3/8', 'XXL', '27 1/2', '1 1/2', 'Add .5 XXL'),

(@project_id1, 'E', 'Sweep / Hem height', '1/8', 'S', '1/2', '0', NULL),
(@project_id1, 'E', 'Sweep / Hem height', '1/8', 'M', '1/2', '0', NULL),
(@project_id1, 'E', 'Sweep / Hem height', '1/8', 'L', '1/2', '0', NULL),
(@project_id1, 'E', 'Sweep / Hem height', '1/8', 'XL', '1/2', '0', NULL),
(@project_id1, 'E', 'Sweep / Hem height', '1/8', 'XXL', '1/2', '0', NULL),

(@project_id1, 'F', 'Across Shoulder - Seam to Seam', '1/4', 'S', '17 3/4', '3/4', NULL),
(@project_id1, 'F', 'Across Shoulder - Seam to Seam', '1/4', 'M', '18 1/2', '3/4', NULL),
(@project_id1, 'F', 'Across Shoulder - Seam to Seam', '1/4', 'L', '19 1/4', '3/4', NULL),
(@project_id1, 'F', 'Across Shoulder - Seam to Seam', '1/4', 'XL', '20', '3/4', NULL),
(@project_id1, 'F', 'Across Shoulder - Seam to Seam', '1/4', 'XXL', '20 3/4', '3/4', NULL),

(@project_id1, 'I-I', 'Sleeve Length From shoulder seam to sleeve edge - WR RIGHT', '1/4', 'S', '24 3/4', '3/4', NULL),
(@project_id1, 'I-I', 'Sleeve Length From shoulder seam to sleeve edge - WR RIGHT', '1/4', 'M', '25 1/2', '3/4', NULL),
(@project_id1, 'I-I', 'Sleeve Length From shoulder seam to sleeve edge - WR RIGHT', '1/4', 'L', '26 1/4', '3/4', NULL),
(@project_id1, 'I-I', 'Sleeve Length From shoulder seam to sleeve edge - WR RIGHT', '1/4', 'XL', '27', '3/4', NULL),
(@project_id1, 'I-I', 'Sleeve Length From shoulder seam to sleeve edge - WR RIGHT', '1/4', 'XXL', '27 3/4', '3/4', NULL),

(@project_id1, 'I-I', 'Sleeve Length From shoulder seam to sleeve edge - WR LEFT', '1/4', 'S', '24 3/4', '3/4', NULL),
(@project_id1, 'I-I', 'Sleeve Length From shoulder seam to sleeve edge - WR LEFT', '1/4', 'M', '25 1/2', '3/4', NULL),
(@project_id1, 'I-I', 'Sleeve Length From shoulder seam to sleeve edge - WR LEFT', '1/4', 'L', '26 1/4', '3/4', NULL),
(@project_id1, 'I-I', 'Sleeve Length From shoulder seam to sleeve edge - WR LEFT', '1/4', 'XL', '27', '3/4', NULL),
(@project_id1, 'I-I', 'Sleeve Length From shoulder seam to sleeve edge - WR LEFT', '1/4', 'XXL', '27 3/4', '3/4', NULL),

(@project_id1, NULL, 'Sleeve Length Difference', '1/4', 'S', '0', '0', NULL),
(@project_id1, NULL, 'Sleeve Length Difference', '1/4', 'M', '0', '0', NULL),
(@project_id1, NULL, 'Sleeve Length Difference', '1/4', 'L', '0', '0', NULL),
(@project_id1, NULL, 'Sleeve Length Difference', '1/4', 'XL', '0', '0', NULL),
(@project_id1, NULL, 'Sleeve Length Difference', '1/4', 'XXL', '0', '0', NULL),

(@project_id1, 'J-1', 'Armhole Drop - Shoulder point to bottom of armhole straight', '1/4', 'S', '9 3/8', '3/8', NULL),
(@project_id1, 'J-1', 'Armhole Drop - Shoulder point to bottom of armhole straight', '1/4', 'M', '9 3/4', '3/8', NULL),
(@project_id1, 'J-1', 'Armhole Drop - Shoulder point to bottom of armhole straight', '1/4', 'L', '10 1/8', '3/8', NULL),
(@project_id1, 'J-1', 'Armhole Drop - Shoulder point to bottom of armhole straight', '1/4', 'XL', '10 1/2', '3/8', NULL),
(@project_id1, 'J-1', 'Armhole Drop - Shoulder point to bottom of armhole straight', '1/4', 'XXL', '10 7/8', '3/8', NULL),

(@project_id1, 'K', 'Muscle - 1" Below Armhole', '1/4', 'S', '8 3/8', '3/8', NULL),
(@project_id1, 'K', 'Muscle - 1" Below Armhole', '1/4', 'M', '8 3/4', '3/8', NULL),
(@project_id1, 'K', 'Muscle - 1" Below Armhole', '1/4', 'L', '9 1/8', '3/8', NULL),
(@project_id1, 'K', 'Muscle - 1" Below Armhole', '1/4', 'XL', '9 1/2', '3/8', NULL),
(@project_id1, 'K', 'Muscle - 1" Below Armhole', '1/4', 'XXL', '9 7/8', '3/8', NULL),

(@project_id1, 'L', 'Elbow, 8" below armhole', '1/4', 'S', '6 5/8', '3/8', NULL),
(@project_id1, 'L', 'Elbow, 8" below armhole', '1/4', 'M', '7', '3/8', NULL),
(@project_id1, 'L', 'Elbow, 8" below armhole', '1/4', 'L', '7 3/8', '3/8', NULL),
(@project_id1, 'L', 'Elbow, 8" below armhole', '1/4', 'XL', '7 3/4', '3/8', NULL),
(@project_id1, 'L', 'Elbow, 8" below armhole', '1/4', 'XXL', '8 1/8', '3/8', NULL),

(@project_id1, NULL, 'Forearm 8" up from sleeve edge', '1/4', 'S', '6 1/8', '1/4', NULL),
(@project_id1, NULL, 'Forearm 8" up from sleeve edge', '1/4', 'M', '6 3/8', '1/4', NULL),
(@project_id1, NULL, 'Forearm 8" up from sleeve edge', '1/4', 'L', '6 5/8', '1/4', NULL),
(@project_id1, NULL, 'Forearm 8" up from sleeve edge', '1/4', 'XL', '6 7/8', '1/4', NULL),
(@project_id1, NULL, 'Forearm 8" up from sleeve edge', '1/4', 'XXL', '7 1/8', '1/4', NULL),

(@project_id1, '0', 'Sleeve opening - buttoned (half meas)', '1/4', 'S', '4 3/4', '1/4', NULL),
(@project_id1, '0', 'Sleeve opening - buttoned (half meas)', '1/4', 'M', '5', '1/4', NULL),
(@project_id1, '0', 'Sleeve opening - buttoned (half meas)', '1/4', 'L', '5 1/4', '1/4', NULL),
(@project_id1, '0', 'Sleeve opening - buttoned (half meas)', '1/4', 'XL', '5 1/2', '1/4', NULL),
(@project_id1, '0', 'Sleeve opening - buttoned (half meas)', '1/4', 'XXL', '5 3/4', '1/4', NULL),

(@project_id1, 'PL-1', 'Sleeve Placket opening length', '1/4', 'S', '3 1/2', '0', NULL),
(@project_id1, 'PL-1', 'Sleeve Placket opening length', '1/4', 'M', '3 1/2', '0', NULL),
(@project_id1, 'PL-1', 'Sleeve Placket opening length', '1/4', 'L', '3 1/2', '0', NULL),
(@project_id1, 'PL-1', 'Sleeve Placket opening length', '1/4', 'XL', '3 1/2', '0', NULL),
(@project_id1, 'PL-1', 'Sleeve Placket opening length', '1/4', 'XXL', '3 1/2', '0', NULL),

(@project_id1, 'PL-2', 'Sleeve Placket Width Finish', '1/8', 'S', '3/8', '0', NULL),
(@project_id1, 'PL-2', 'Sleeve Placket Width Finish', '1/8', 'M', '3/8', '0', NULL),
(@project_id1, 'PL-2', 'Sleeve Placket Width Finish', '1/8', 'L', '3/8', '0', NULL),
(@project_id1, 'PL-2', 'Sleeve Placket Width Finish', '1/8', 'XL', '3/8', '0', NULL),
(@project_id1, 'PL-2', 'Sleeve Placket Width Finish', '1/8', 'XXL', '3/8', '0', NULL),

(@project_id1, 'M.', 'Cuff Height', '1/8', 'S', '2 1/2', '0', NULL),
(@project_id1, 'M.', 'Cuff Height', '1/8', 'M', '2 1/2', '0', NULL),
(@project_id1, 'M.', 'Cuff Height', '1/8', 'L', '2 1/2', '0', NULL),
(@project_id1, 'M.', 'Cuff Height', '1/8', 'XL', '2 1/2', '0', NULL),
(@project_id1, 'M.', 'Cuff Height', '1/8', 'XXL', '2 1/2', '0', NULL),

(@project_id1, 'Q-5', 'Neck Width, seam to seam', '1/4', 'S', '6 3/4', '1/4', NULL),
(@project_id1, 'Q-5', 'Neck Width, seam to seam', '1/4', 'M', '7', '1/4', NULL),
(@project_id1, 'Q-5', 'Neck Width, seam to seam', '1/4', 'L', '7 1/4', '1/4', NULL),
(@project_id1, 'Q-5', 'Neck Width, seam to seam', '1/4', 'XL', '7 1/2', '1/4', NULL),
(@project_id1, 'Q-5', 'Neck Width, seam to seam', '1/4', 'XXL', '7 3/4', '1/4', NULL),

(@project_id1, 'U', 'Front Neck Drop - HPS to seam', '1/4', 'S', '3 1/2', '1/4', NULL),
(@project_id1, 'U', 'Front Neck Drop - HPS to seam', '1/4', 'M', '3 3/4', '1/4', NULL),
(@project_id1, 'U', 'Front Neck Drop - HPS to seam', '1/4', 'L', '4', '1/4', NULL),
(@project_id1, 'U', 'Front Neck Drop - HPS to seam', '1/4', 'XL', '4 1/4', '1/4', NULL),
(@project_id1, 'U', 'Front Neck Drop - HPS to seam', '1/4', 'XXL', '4 1/2', '1/4', NULL),

(@project_id1, 'V', 'Back Neck Drop - HPS to seam', '1/4', 'S', '1/2', '0', 'Add .125 to L, XL, XXL'),
(@project_id1, 'V', 'Back Neck Drop - HPS to seam', '1/4', 'M', '1/2', '0', 'Add .125 to L, XL, XXL'),
(@project_id1, 'V', 'Back Neck Drop - HPS to seam', '1/4', 'L', '5/8', '0', 'Add .125 to L, XL, XXL'),
(@project_id1, 'V', 'Back Neck Drop - HPS to seam', '1/4', 'XL', '5/8', '0', 'Add .125 to L, XL, XXL'),
(@project_id1, 'V', 'Back Neck Drop - HPS to seam', '1/4', 'XXL', '5/8', '0', 'Add .125 to L, XL, XXL'),

(@project_id1, 'Q-6', 'Collar length along top edge', '1/4', 'S', '18 3/8', '7/8', NULL),
(@project_id1, 'Q-6', 'Collar length along top edge', '1/4', 'M', '19 1/4', '7/8', NULL),
(@project_id1, 'Q-6', 'Collar length along top edge', '1/4', 'L', '20 1/4', '7/8', NULL),
(@project_id1, 'Q-6', 'Collar length along top edge', '1/4', 'XL', '21 1/8', '7/8', NULL),
(@project_id1, 'Q-6', 'Collar length along top edge', '1/4', 'XXL', '22', '7/8', NULL),

(@project_id1, 'Q-1', 'Collar Point', '1/4', 'S', '2 3/4', '0', NULL),
(@project_id1, 'Q-1', 'Collar Point', '1/4', 'M', '2 3/4', '0', NULL),
(@project_id1, 'Q-1', 'Collar Point', '1/4', 'L', '2 3/4', '0', NULL),
(@project_id1, 'Q-1', 'Collar Point', '1/4', 'XL', '2 3/4', '0', NULL),
(@project_id1, 'Q-1', 'Collar Point', '1/4', 'XXL', '2 3/4', '0', NULL),

(@project_id1, 'N', 'Collar Height Center Back', '1/8', 'S', '2 1/4', '0', NULL),
(@project_id1, 'N', 'Collar Height Center Back', '1/8', 'M', '2 1/4', '0', NULL),
(@project_id1, 'N', 'Collar Height Center Back', '1/8', 'L', '2 1/4', '0', NULL),
(@project_id1, 'N', 'Collar Height Center Back', '1/8', 'XL', '2 1/4', '0', NULL),
(@project_id1, 'N', 'Collar Height Center Back', '1/8', 'XXL', '2 1/4', '0', NULL),

(@project_id1, 'Q-7', 'Collar Stand Height at Center Back', '1/8', 'S', '1 1/4', '0', NULL),
(@project_id1, 'Q-7', 'Collar Stand Height at Center Back', '1/8', 'M', '1 1/4', '0', NULL),
(@project_id1, 'Q-7', 'Collar Stand Height at Center Back', '1/8', 'L', '1 1/4', '0', NULL),
(@project_id1, 'Q-7', 'Collar Stand Height at Center Back', '1/8', 'XL', '1 1/4', '0', NULL),
(@project_id1, 'Q-7', 'Collar Stand Height at Center Back', '1/8', 'XXL', '1 1/4', '0', NULL),

(@project_id1, 'PW', 'Front Placket width', '1/8', 'S', '1 1/2', '0', NULL),
(@project_id1, 'PW', 'Front Placket width', '1/8', 'M', '1 1/2', '0', NULL),
(@project_id1, 'PW', 'Front Placket width', '1/8', 'L', '1 1/2', '0', NULL),
(@project_id1, 'PW', 'Front Placket width', '1/8', 'XL', '1 1/2', '0', NULL),
(@project_id1, 'PW', 'Front Placket width', '1/8', 'XXL', '1 1/2', '0', NULL),

(@project_id1, 'W-1', 'Shoulder Forward', '1/4', 'S', '2', '0', 'Add .25 to XL, XXL'),
(@project_id1, 'W-1', 'Shoulder Forward', '1/4', 'M', '2', '0', 'Add .25 to XL, XXL'),
(@project_id1, 'W-1', 'Shoulder Forward', '1/4', 'L', '2', '0', 'Add .25 to XL, XXL'),
(@project_id1, 'W-1', 'Shoulder Forward', '1/4', 'XL', '2 1/4', '0', 'Add .25 to XL, XXL'),
(@project_id1, 'W-1', 'Shoulder Forward', '1/4', 'XXL', '2 1/4', '0', 'Add .25 to XL, XXL'),

(@project_id1, 'H-3', 'Center back yoke height', '1/4', 'S', '6', '0', 'Add .5 to XL, XXL'),
(@project_id1, 'H-3', 'Center back yoke height', '1/4', 'M', '6', '0', 'Add .5 to XL, XXL'),
(@project_id1, 'H-3', 'Center back yoke height', '1/4', 'L', '6', '0', 'Add .5 to XL, XXL'),
(@project_id1, 'H-3', 'Center back yoke height', '1/4', 'XL', '6 1/2', '0', 'Add .5 to XL, XXL'),
(@project_id1, 'H-3', 'Center back yoke height', '1/4', 'XXL', '6 1/2', '0', 'Add .5 to XL, XXL'),

(@project_id1, 'PK-5', 'Pocket Width', '1/4', 'S', '5 3/8', '0', 'Add .25 to XL, XXL'),
(@project_id1, 'PK-5', 'Pocket Width', '1/4', 'M', '5 3/8', '0', 'Add .25 to XL, XXL'),
(@project_id1, 'PK-5', 'Pocket Width', '1/4', 'L', '5 3/8', '0', 'Add .25 to XL, XXL'),
(@project_id1, 'PK-5', 'Pocket Width', '1/4', 'XL', '5 5/8', '0', 'Add .25 to XL, XXL'),
(@project_id1, 'PK-5', 'Pocket Width', '1/4', 'XXL', '5 5/8', '0', 'Add .25 to XL, XXL'),

(@project_id1, 'PK-4', 'Pkt Height at Center including flap**', '1/4', 'S', '6 3/4', '0', 'Add .25 to XL, XXL'),
(@project_id1, 'PK-4', 'Pkt Height at Center including flap**', '1/4', 'M', '6 3/4', '0', 'Add .25 to XL, XXL'),
(@project_id1, 'PK-4', 'Pkt Height at Center including flap**', '1/4', 'L', '6 3/4', '0', 'Add .25 to XL, XXL'),
(@project_id1, 'PK-4', 'Pkt Height at Center including flap**', '1/4', 'XL', '7', '0', 'Add .25 to XL, XXL'),
(@project_id1, 'PK-4', 'Pkt Height at Center including flap**', '1/4', 'XXL', '7', '0', 'Add .25 to XL, XXL'),

(@project_id1, 'PK-11', 'Pkt Flap Height at center', '1/4', 'S', '2 3/4', '0', 'Add .125 to XL, XXL'),
(@project_id1, 'PK-11', 'Pkt Flap Height at center', '1/4', 'M', '2 3/4', '0', 'Add .125 to XL, XXL'),
(@project_id1, 'PK-11', 'Pkt Flap Height at center', '1/4', 'L', '2 3/4', '0', 'Add .125 to XL, XXL'),
(@project_id1, 'PK-11', 'Pkt Flap Height at center', '1/4', 'XL', '2 7/8', '0', 'Add .125 to XL, XXL'),
(@project_id1, 'PK-11', 'Pkt Flap Height at center', '1/4', 'XXL', '2 7/8', '0', 'Add .125 to XL, XXL'),

(@project_id1, 'PK-12', 'Pkt flap height at sides', '1/4', 'S', '2', '0', 'Add .125 to XL, XXL'),
(@project_id1, 'PK-12', 'Pkt flap height at sides', '1/4', 'M', '2', '0', 'Add .125 to XL, XXL'),
(@project_id1, 'PK-12', 'Pkt flap height at sides', '1/4', 'L', '2', '0', 'Add .125 to XL, XXL'),
(@project_id1, 'PK-12', 'Pkt flap height at sides', '1/4', 'XL', '2 1/8', '0', 'Add .125 to XL, XXL'),
(@project_id1, 'PK-12', 'Pkt flap height at sides', '1/4', 'XXL', '2 1/8', '0', 'Add .125 to XL, XXL'),

(@project_id1, 'PK-4', 'Pkt flap width at top', '1/4', 'S', '5 5/8', '0', 'Add .25 to XL, XXL'),
(@project_id1, 'PK-4', 'Pkt flap width at top', '1/4', 'M', '5 5/8', '0', 'Add .25 to XL, XXL'),
(@project_id1, 'PK-4', 'Pkt flap width at top', '1/4', 'L', '5 5/8', '0', 'Add .25 to XL, XXL'),
(@project_id1, 'PK-4', 'Pkt flap width at top', '1/4', 'XL', '5 7/8', '0', 'Add .25 to XL, XXL'),
(@project_id1, 'PK-4', 'Pkt flap width at top', '1/4', 'XXL', '5 7/8', '0', 'Add .25 to XL, XXL'),

(@project_id1, 'PK-11', 'Pkt Placement from HPS', '1/4', 'S', '8', '1/4', NULL),
(@project_id1, 'PK-11', 'Pkt Placement from HPS', '1/4', 'M', '8 1/4', '1/4', NULL),
(@project_id1, 'PK-11', 'Pkt Placement from HPS', '1/4', 'L', '8 1/2', '1/4', NULL),
(@project_id1, 'PK-11', 'Pkt Placement from HPS', '1/4', 'XL', '8 3/4', '1/4', NULL),
(@project_id1, 'PK-11', 'Pkt Placement from HPS', '1/4', 'XXL', '9', '1/4', NULL),

(@project_id1, 'PK-12', 'Pkt placement from Center Front', '1/4', 'S', '2', '1/4', 'S=M'),
(@project_id1, 'PK-12', 'Pkt placement from Center Front', '1/4', 'M', '2', '1/4', 'S=M'),
(@project_id1, 'PK-12', 'Pkt placement from Center Front', '1/4', 'L', '2 1/4', '1/4', 'S=M'),
(@project_id1, 'PK-12', 'Pkt placement from Center Front', '1/4', 'XL', '2 1/2', '1/4', 'S=M'),
(@project_id1, 'PK-12', 'Pkt placement from Center Front', '1/4', 'XXL', '2 3/4', '1/4', 'S=M'),

(@project_id1, NULL, 'Pkt welt width', '1/4', 'S', '3/4', '0', NULL),
(@project_id1, NULL, 'Pkt welt width', '1/4', 'M', '3/4', '0', NULL),
(@project_id1, NULL, 'Pkt welt width', '1/4', 'L', '3/4', '0', NULL),
(@project_id1, NULL, 'Pkt welt width', '1/4', 'XL', '3/4', '0', NULL),
(@project_id1, NULL, 'Pkt welt width', '1/4', 'XXL', '3/4', '0', NULL),

(@project_id1, NULL, 'Pkt welt length', '1/4', 'S', '6 3/4', '0', 'Add .125 to XL, XXL'),
(@project_id1, NULL, 'Pkt welt length', '1/4', 'M', '6 3/4', '0', 'Add .125 to XL, XXL'),
(@project_id1, NULL, 'Pkt welt length', '1/4', 'L', '6 3/4', '0', 'Add .125 to XL, XXL'),
(@project_id1, NULL, 'Pkt welt length', '1/4', 'XL', '6 7/8', '0', 'Add .125 to XL, XXL'),
(@project_id1, NULL, 'Pkt welt length', '1/4', 'XXL', '6 7/8', '0', 'Add .125 to XL, XXL'),

(@project_id1, NULL, 'Pkt welt up from bottom edge of garment', '1/4', 'S', '4 3/4', '0', 'Add .5 to XL, XXL'),
(@project_id1, NULL, 'Pkt welt up from bottom edge of garment', '1/4', 'M', '4 3/4', '0', 'Add .5 to XL, XXL'),
(@project_id1, NULL, 'Pkt welt up from bottom edge of garment', '1/4', 'L', '4 3/4', '0', 'Add .5 to XL, XXL'),
(@project_id1, NULL, 'Pkt welt up from bottom edge of garment', '1/4', 'XL', '5 1/4', '0', 'Add .5 to XL, XXL'),
(@project_id1, NULL, 'Pkt welt up from bottom edge of garment', '1/4', 'XXL', '5 1/4', '0', 'Add .5 to XL, XXL'),

(@project_id1, NULL, 'Top edge of welt from side seam', '1/4', 'S', '3', '1/4', 'S=M'),
(@project_id1, NULL, 'Top edge of welt from side seam', '1/4', 'M', '3', '1/4', 'S=M'),
(@project_id1, NULL, 'Top edge of welt from side seam', '1/4', 'L', '3 1/4', '1/4', 'S=M'),
(@project_id1, NULL, 'Top edge of welt from side seam', '1/4', 'XL', '3 1/2', '1/4', 'S=M'),
(@project_id1, NULL, 'Top edge of welt from side seam', '1/4', 'XXL', '3 3/4', '1/4', 'S=M'),

(@project_id1, NULL, 'Bottom edge of welt from side seam', '1/4', 'S', '2 1/2', '1/4', 'S=M'),
(@project_id1, NULL, 'Bottom edge of welt from side seam', '1/4', 'M', '2 1/2', '1/4', 'S=M'),
(@project_id1, NULL, 'Bottom edge of welt from side seam', '1/4', 'L', '2 3/4', '1/4', 'S=M'),
(@project_id1, NULL, 'Bottom edge of welt from side seam', '1/4', 'XL', '3', '1/4', 'S=M'),
(@project_id1, NULL, 'Bottom edge of welt from side seam', '1/4', 'XXL', '3 1/4', '1/4', 'S=M');
