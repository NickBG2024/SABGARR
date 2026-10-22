<?php
if (!defined('ABSPATH')) { exit; }

final class SABGA_Matches {
    private static $file;
    public static function boot($file) {
        self::$file = $file;
        add_action('rest_api_init', array(__CLASS__, 'routes'));
    }

    public static function fixtures_sql() {
        return 'SELECT f.FixtureID AS fixture_id, f.Player1ID AS p1_id, f.Player2ID AS p2_id,
            f.Completed AS completed, p1.Name AS p1_name, p1.Nickname AS p1_nickname,
            p2.Name AS p2_name, p2.Nickname AS p2_nickname,
            EXISTS(SELECT 1 FROM MatchResults r WHERE r.FixtureID=f.FixtureID AND r.MatchTypeID=f.MatchTypeID) AS has_result
            FROM Fixtures f LEFT JOIN Players p1 ON p1.PlayerID=f.Player1ID
            LEFT JOIN Players p2 ON p2.PlayerID=f.Player2ID
            WHERE f.MatchTypeID=? ORDER BY p1.Name,p2.Name,f.FixtureID LIMIT 2001';
    }

    public static function results_sql() {
        // Keep each result's player order, scores and PRs together, even if the fixture order differs.
        return 'SELECT mr.MatchResultID AS result_id, mr.FixtureID AS fixture_id, mr.Date AS date,
            mr.Player1ID AS p1_id,mr.Player2ID AS p2_id,p1.Name AS p1_name,p1.Nickname AS p1_nickname,
            p2.Name AS p2_name,p2.Nickname AS p2_nickname,mr.Player1Points AS p1_score,
            mr.Player2Points AS p2_score,mr.Player1PR AS p1_pr,mr.Player2PR AS p2_pr
            FROM MatchResults mr JOIN Fixtures f ON f.FixtureID=mr.FixtureID AND f.MatchTypeID=mr.MatchTypeID
            LEFT JOIN Players p1 ON p1.PlayerID=mr.Player1ID LEFT JOIN Players p2 ON p2.PlayerID=mr.Player2ID
            WHERE mr.MatchTypeID=? AND f.Completed=1 ORDER BY mr.Date DESC,mr.MatchResultID DESC LIMIT 2001';
    }

    public static function validate($input) {
        $scope = $input['scope'] ?? 'current'; $view = $input['view'] ?? 'remaining';
        if (!is_string($scope) || !in_array($scope,array('current','history'),true) || !is_string($view) || !in_array($view,array('remaining','results'),true)) {
            return new WP_Error('sabga_matches_selection','Choose a valid fixtures or results view.',array('status'=>400));
        }
        $group=SABGA_History::integer($input['group'] ?? '');
        if($scope==='current') {
            if(!SABGA_Leagues::valid_group($group)){return new WP_Error('sabga_matches_selection','Choose a current league group.',array('status'=>400));}
        } else {
            $catalog=SABGA_History::catalog(); if(is_wp_error($catalog)){return $catalog;}
            if(!isset($input['season'],$input['series'],$input['group'])){return new WP_Error('sabga_matches_selection','Choose a season, series and group.',array('status'=>400));}
            $selection=SABGA_History::select($catalog,array('tab'=>'standings','season'=>$input['season'],'series'=>$input['series'],'group'=>$group));
            if(is_wp_error($selection)){return $selection;}
            if(!$selection['has_previous']){return new WP_Error('sabga_matches_selection','No previous series is available.',array('status'=>400));}
        }
        $player=$input['player'] ?? '0';
        if(!is_scalar($player) || ((string)$player!=='0' && !SABGA_History::integer($player))){return new WP_Error('sabga_matches_selection','Choose a valid player filter.',array('status'=>400));}
        return array('scope'=>$scope,'view'=>$view,'group'=>$group,'player'=>(int)$player);
    }

    private static function demo_rows() {
        $base=array('p1_id'=>1,'p2_id'=>2,'p1_name'=>'Demo Player One','p1_nickname'=>'example1','p2_name'=>'Demo Player Two','p2_nickname'=>'example2');
        return array(
            array(array_merge($base,array('fixture_id'=>1,'completed'=>0,'has_result'=>0)),
                array_merge($base,array('fixture_id'=>2,'p2_id'=>3,'p2_name'=>'Demo Player Three','p2_nickname'=>'example3','completed'=>0,'has_result'=>0)),
                array_merge($base,array('fixture_id'=>3,'completed'=>1,'has_result'=>1))),
            array(array_merge($base,array('result_id'=>1,'fixture_id'=>3,'date'=>'2026-10-01','p1_score'=>8,'p2_score'=>11,'p1_pr'=>null,'p2_pr'=>6.12)))
        );
    }

    private static function label($r,$side) {
        return ($r[$side.'_name'] ?? ('Unknown player #' . $r[$side.'_id'])) .
            (!empty($r[$side.'_nickname'])?' (' . $r[$side.'_nickname'] . ')':'');
    }

    public static function format($fixtures,$results,$selection) {
        if(count($fixtures)>2000 || count($results)>2000){return new WP_Error('sabga_matches_limit','This group has more than 2,000 records. Ask the administrator to add pagination before displaying it.',array('status'=>422));}
        $players=array();
        foreach(array_merge($fixtures,$results) as $r){foreach(array('p1','p2') as $side){$id=(int)$r[$side.'_id'];if($id>0){$players[$id]=array('id'=>$id,'label'=>self::label($r,$side));}}}
        uasort($players,function($a,$b){return strcasecmp($a['label'],$b['label']) ?: ($a['id'] <=> $b['id']);});
        if($selection['player'] && !isset($players[$selection['player']])){return new WP_Error('sabga_matches_selection','Choose a player from this league group.',array('status'=>400));}
        $remaining=array();$missing=0;$open_results=0;$unknown=0;
        foreach($fixtures as $r){
            if($r['completed']!==null && (int)$r['completed']===0){$remaining[]=$r; if((int)$r['has_result']){$open_results++;}}
            if((int)$r['completed']===1 && !(int)$r['has_result']){$missing++;}
            if($r['completed']===null || !in_array((int)$r['completed'],array(0,1),true)){$unknown++;}
        }
        $source=$selection['view']==='remaining'?$remaining:$results;$rows=array();$lines=array();$groups=array();
        foreach($source as $r){
            if($selection['player'] && $selection['player']!==(int)$r['p1_id'] && $selection['player']!==(int)$r['p2_id']){continue;}
            if($selection['view']==='remaining'){
                $warning=(int)$r['has_result']?'Result recorded; fixture still open':'';
                $rows[]=array(self::label($r,'p1'),self::label($r,'p2'),$warning ?: 'Unplayed');
                $lines[]=self::label($r,'p1').' vs '.self::label($r,'p2').($warning?' ['.$warning.']':'');
                foreach(array('p1'=>'p2','p2'=>'p1') as $side=>$other){
                    $pid=(int)$r[$side.'_id'];
                    if($selection['player'] && $selection['player']!==$pid){continue;}
                    if(!isset($groups[$pid])){$groups[$pid]=array('player'=>self::label($r,$side),'opponents'=>array());}
                    $groups[$pid]['opponents'][]=self::label($r,$other).($warning?' ['.$warning.']':'');
                }
            } else {
                $score=($r['p1_score']===null?'—':(int)$r['p1_score']).' – '.($r['p2_score']===null?'—':(int)$r['p2_score']);
                $rows[]=array($r['date'] ?: '—',self::label($r,'p1'),$score,self::label($r,'p2'),SABGA_History::decimal($r['p1_pr']),SABGA_History::decimal($r['p2_pr']));
            }
        }
        $note=$selection['view']==='remaining' ? ($selection['scope']==='history'?'Unplayed fixtures retained from this previous series.':'Outstanding fixtures in the selected league group.') : 'Newest results first. Scores and PRs follow Player 1 / Player 2 order; a dash means no value was recorded.';
        if($open_results){$note.=' '.$open_results.' open fixture(s) already have a result and need an administrator check.';}
        if($unknown){$note.=' '.$unknown.' fixture(s) have an unknown completion status.';}
        if($missing){$note.=' '.$missing.' completed fixture(s) have no linked result.';}
        uasort($groups,function($a,$b){return strcasecmp($a['player'],$b['player']);});
        return array('layout'=>$selection['view']==='remaining'?'fixture-list':'table','fixture_lines'=>$lines,'fixture_groups'=>array_values($groups),'copy_text'=>implode("\n",$lines),
            'columns'=>$selection['view']==='remaining'?array('Player 1','Player 2','Status'):array('Date','Player 1','Score','Player 2','PR 1','PR 2'),
            'rows'=>$rows,'players'=>array_values($players),'player'=>$selection['player'],'note'=>$note,
            'count'=>count($rows),'total'=>count($source),'empty'=>$selection['view']==='remaining'?'No outstanding fixtures for this selection.':'No recorded results for this selection.');
    }

    public static function payload($input) {
        $selection=self::validate($input);if(is_wp_error($selection)){return $selection;}
        if(SABGA_Leagues::mode()==='demo'){list($fixtures,$results)=self::demo_rows();return self::format($fixtures,$results,$selection);}
        $key=SABGA_Leagues::cache_key($selection['group']).'_matches';$raw=get_transient($key);
        if(!is_array($raw)){
            try{
                $db=SABGA_History::connection();$st=$db->prepare(self::fixtures_sql());$st->execute(array($selection['group']));$fixtures=$st->fetchAll();
                $st=$db->prepare(self::results_sql());$st->execute(array($selection['group']));$results=$st->fetchAll();
                $raw=array($fixtures,$results);if(count($fixtures)<=2000 && count($results)<=2000){set_transient($key,$raw,60);}
            }catch(Throwable $error){return new WP_Error('sabga_matches_database','Fixtures and results could not be loaded. Ask the site administrator to check the league database read permissions.',array('status'=>503));}
        }
        return self::format($raw[0],$raw[1],$selection);
    }

    public static function routes() {
        register_rest_route('sabga-leagues/v1','/matches',array('methods'=>'GET','permission_callback'=>'__return_true','callback'=>function($request){
            $input=array();foreach(array('scope','view','group','season','series','player') as $key){$v=$request->get_param($key);if($v!==null){$input[$key]=$v;}}
            $data=self::payload($input);if(is_wp_error($data)){return $data;}$response=new WP_REST_Response($data);$response->header('Cache-Control','no-store, max-age=0');return $response;
        }));
    }

    public static function current_view($scope) {
        $key=$scope==='current'?'sabga_view':'sabga_history_view';$view=$_GET[$key] ?? 'standings';
        return is_string($view) && in_array($view,array('standings','remaining','results'),true)?$view:'standings';
    }

    public static function nav($context) {
        wp_enqueue_style('sabga-matches',plugins_url('assets/matches.css',self::$file),array(),SABGA_Leagues::VERSION);
        wp_enqueue_script('sabga-matches',plugins_url('assets/matches.js',self::$file),array(),SABGA_Leagues::VERSION,true);
        if(did_action('wp_head') && !wp_style_is('sabga-matches','done')){wp_print_styles('sabga-matches');}
        $view=self::current_view($context['scope']);$key=$context['scope']==='current'?'sabga_view':'sabga_history_view';
        $html='<nav class="sabga-matches__tabs" aria-label="League views">';
        foreach(array('standings'=>'Standings','remaining'=>'Remaining Fixtures','results'=>'Results') as $v=>$title){
            $args=array($key=>$v,'sabga_match_player'=>false,'sabga_history_match_player'=>false);
            if($context['scope']==='current'){$args['sabga_group']=$context['group'];}else{$args+=array('sabga_history_tab'=>'standings','sabga_history_season'=>$context['season'],'sabga_history_series'=>$context['series'],'sabga_history_group'=>$context['group']);}
            $html.='<a href="'.esc_url(add_query_arg($args)).'" data-match-view="'.esc_attr($v).'"'.($v===$view?' aria-current="page"':'').'>'.esc_html($title).'</a>';
        }
        return $html.'</nav>';
    }

    public static function panel($context) {
        $view=self::current_view($context['scope']);$player_key=$context['scope']==='current'?'sabga_match_player':'sabga_history_match_player';
        $input=$context+array('view'=>$view==='standings'?'remaining':$view,'player'=>$_GET[$player_key] ?? '0');
        $data=$view==='standings'?null:self::payload($input);$uid=wp_unique_id('sabga-match-player-');ob_start(); ?>
        <div class="sabga-matches" data-context="<?php echo esc_attr(json_encode($context)); ?>" data-endpoint="<?php echo esc_url(rest_url('sabga-leagues/v1/matches')); ?>" data-view="<?php echo esc_attr($view); ?>" <?php echo $view==='standings'?'hidden':''; ?>>
        <h3 class="sabga-matches__heading"><?php echo $view==='results'?'Results':'Remaining Fixtures'; ?></h3>
        <form method="get" class="sabga-matches__filter">
        <?php if(!get_option('permalink_structure') && get_queried_object_id()):?><input type="hidden" name="page_id" value="<?php echo esc_attr(get_queried_object_id()); ?>"><?php endif; ?>
        <?php $args=$context['scope']==='current'?array('sabga_group'=>$context['group'],'sabga_view'=>$view):array('sabga_history_tab'=>'standings','sabga_history_season'=>$context['season'],'sabga_history_series'=>$context['series'],'sabga_history_group'=>$context['group'],'sabga_history_view'=>$view); foreach($args as $k=>$v):?><input type="hidden" name="<?php echo esc_attr($k); ?>" value="<?php echo esc_attr($v); ?>"><?php endforeach; ?>
        <label for="<?php echo esc_attr($uid); ?>">Filter by player</label><select id="<?php echo esc_attr($uid); ?>" name="<?php echo esc_attr($player_key); ?>"><option value="0">All players</option><?php if(is_array($data)):foreach($data['players'] as $p):?><option value="<?php echo esc_attr($p['id']); ?>" <?php selected($data['player'],$p['id']); ?>><?php echo esc_html($p['label']); ?></option><?php endforeach;endif; ?></select><button type="submit">Show matches</button></form>
        <p class="sabga-matches__status" role="status" aria-live="polite"></p>
        <div class="sabga-matches__report"><?php if(is_wp_error($data)){echo '<p role="alert">'.esc_html($data->get_error_message()).'</p>';}elseif(is_array($data)){echo self::table($data);} ?></div>
        </div><?php return ob_get_clean();
    }

    public static function table($data) {
        $html='<p>'.esc_html($data['count'].' of '.$data['total'].' matches').'</p><p class="sabga-matches__note">'.esc_html($data['note']).'</p>';
        if(!$data['rows']){return $html.'<p>'.esc_html($data['empty']).'</p>';}
        if(($data['layout'] ?? '')==='fixture-list'){
            $html.='<button type="button" class="sabga-matches__copy" data-copy-fixtures hidden>Copy fixtures</button><p class="sabga-matches__copy-status" role="status" aria-live="polite"></p>';
            $html.='<textarea class="sabga-matches__copy-text" data-copy-text aria-label="Fixtures to copy" readonly hidden>'.esc_html($data['copy_text']).'</textarea>';
            $html.='<ul class="sabga-matches__fixture-list">';foreach($data['fixture_lines'] as $line){$html.='<li>'.esc_html($line).'</li>';}$html.='</ul>';
            $html.='<details class="sabga-matches__by-player"><summary>View by player</summary><p class="sabga-matches__note">Each pairing appears under both players. Counts below are per player.</p><dl>';
            foreach($data['fixture_groups'] as $g){$html.='<div><dt>'.esc_html($g['player']).' <span>('.count($g['opponents']).' remaining)</span></dt><dd>'.esc_html(implode(', ',$g['opponents'])).'</dd></div>';}
            return $html.'</dl></details>';
        }
        $html.='<div class="sabga-matches__scroll" tabindex="0" role="region" aria-label="Fixtures and results; scroll for more columns"><table><caption>League matches</caption><thead><tr>';
        foreach($data['columns'] as $c){$html.='<th scope="col">'.esc_html($c).'</th>';}$html.='</tr></thead><tbody>';
        foreach($data['rows'] as $r){$html.='<tr>';foreach($r as $v){$html.='<td>'.esc_html($v).'</td>';}$html.='</tr>';}
        return $html.'</tbody></table></div>';
    }
}
