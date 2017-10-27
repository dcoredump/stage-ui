#!/usr/bin/perl

use Data::Dumper;

open(TTL,"<$ARGV[0]") || die("Cannot open $ARGV[0]\n");
while($ttl=<TTL>)
{
	chop($ttl);

    if($ttl=~/^<(.+)>\s*$/)
    {
        print "$1";
    }
}
