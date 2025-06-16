{pkgs}: {
  deps = [
    pkgs.jq
    pkgs.rustc
    pkgs.libiconv
    pkgs.cargo
    pkgs.wireshark
    pkgs.tcpdump
    pkgs.sox
    pkgs.imagemagickBig
    pkgs.glibcLocales
    pkgs.postgresql
    pkgs.openssl
  ];
}
