#!/usr/bin/perl

use strict;
use Data::Dumper;
use HTTP::Tiny;
use DBI;

my $mysql_user = "perluser";
my $mysql_pwd = "koikaravlaka";
my $frommail = 'futureyou@yournewjob.com';
my $tomail = 'hristo.slavov@opencode.com';
my $db = "DBI:mysql:database=jobsa;host=localhost;port=3306";
my $dbh = DBI->connect($db,$mysql_user,$mysql_pwd,{RaiseError => 0, PrintError => 0, mysql_enable_utf8 => 1});

my $url = 'https://www.jobs.bg/front_job_search.php?first_search=1&distance=0&location_sid=1&categories[]=15&categories[]=16&categories[]=43&all_type=0&all_position_level=1&keyword=linux';
my $site = 'https://www.jobs.bg';
my $job_site = 'https://www.jobs.bg/f';
my $search_page = HTTP::Tiny->new->get($url);
my $html;
if ($search_page->{success}) {
	$html = $search_page->{content};
}

my $count = 0;
my @pages;
my @pages_content;
my $frontpage = 0;
while ($html =~ m/a\shref=\"(.*?)\"\s*class=pathlink/g) {
	my $tmp_url = $1;
	$tmp_url =~ m/\?frompage=(\d{1,3})\&/;
	if($frontpage <= $1){
		$frontpage = $1;
		$pages[$count] = $site.$tmp_url;
		my $next_page = HTTP::Tiny->new->get($pages[$count]);
		if ($search_page->{success}) {
		       $pages_content[$count] = $next_page->{content};
		}
	} else{
		last;
	}
	$count++;
}

my @company_name;
my @job_name;
my @job_id;
my @company_offer;
my $cmp_cnt = 0;

unshift @pages_content, $html;
foreach my $pager(@pages_content){
	while ($pager =~ m/<a\shref=\"f(\d{1,10}?)\"\sclass=\"joblink\".*?>(.*?)<\/a>/g){
		$job_id[$cmp_cnt] = $1;
	        $job_name[$cmp_cnt] = $2;
		my $sth = 'SELECT offer_id FROM offers WHERE offer_id = '.$job_id[$cmp_cnt];
		if($dbh->selectrow_array($sth)){
			next;
		} else{
			my $insert_query = $dbh->prepare('insert into offers values(?,?)');
			$insert_query->execute($job_id[$cmp_cnt],$job_name[$cmp_cnt]);
		}
		my $offer_url = $job_site.$job_id[$cmp_cnt];
		my $offer_page = HTTP::Tiny->new->get($offer_url);
		my $offer_html;
		if ($offer_page->{success}) {
        		$offer_html = $offer_page->{content};
			$offer_html =~ m/(<body.*?<\/body>)/isg;
		        $company_offer[$cmp_cnt] = $1;
#        		$company_offer[$cmp_cnt] =~ s/<script.*?<\/script>//isg;
#        		$company_offer[$cmp_cnt] =~ s/<style.*?<\/style>//isg;
			$company_offer[$cmp_cnt] = "<html>".$company_offer[$cmp_cnt]."</html>";
			open(MAIL, "|/usr/sbin/sendmail -t");
			print MAIL "To: $tomail\n";
			print MAIL "From: $frommail\n";
			print MAIL "Subject: $job_name[$cmp_cnt]\n";
			print MAIL "Content-type: text/html\n";
			print MAIL $company_offer[$cmp_cnt];
			close(MAIL);
		} else{
			print $offer_url."cannot be opened.";
			next;
		}
		$cmp_cnt++;
	}
}
$dbh->disconnect();

#print Dumper(@pages);
#print Dumper(@company_name);
#print Dumper(@company_offer);
