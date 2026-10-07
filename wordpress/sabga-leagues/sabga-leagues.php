<?php
/**
 * Plugin Name: SABGA League Standings
 * Description: Read-only SQL standings with a clearly labelled demo mode. Proof of concept for SABGA's WordPress league page.
 * Version: 0.1.2
 * Requires at least: 6.0
 * Requires PHP: 7.4
 * Author: SABGA
 * License: GPL-2.0-or-later
 * Text Domain: sabga-leagues
 */

if (!defined('ABSPATH')) { exit; }
require_once __DIR__ . '/includes/class-sabga-leagues.php';
SABGA_Leagues::boot(__FILE__);
