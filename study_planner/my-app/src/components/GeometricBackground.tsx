const GeometricBackground = () => {
  return (
    <>
      {/* Large blue circle on the left */}
      <div className="absolute left-0 top-0 -translate-x-1/2 -translate-y-1/4 w-[500px] h-[500px] md:w-[650px] md:h-[650px] rounded-full bg-primary opacity-90">
        <div className="absolute top-[15%] left-[15%] w-12 h-12 rounded-full bg-accent"></div>
      </div>

      {/* Diagonal stripes top right */}
      <div className="absolute top-0 right-0 w-[280px] h-[280px] md:w-[350px] md:h-[350px] overflow-hidden">
        <div className="absolute -top-10 -right-10 w-18 h-[450px] bg-primary rotate-45 transform origin-top-right"></div>
        <div className="absolute top-8 -right-10 w-18 h-[450px] bg-primary rotate-45 transform origin-top-right"></div>
        <div className="absolute top-28 -right-10 w-18 h-[450px] bg-primary rotate-45 transform origin-top-right"></div>
        <div className="absolute top-44 -right-10 w-16 h-[400px] bg-primary rotate-45 transform origin-top-right"></div>
      </div>

      {/* Light purple triangular shapes bottom right */}
      <div className="absolute bottom-0 right-0 w-[320px] h-[320px] md:w-[400px] md:h-[400px] overflow-hidden">
        <div className="absolute bottom-0 right-0">
          <div className="w-0 h-0 border-l-[190px] border-l-transparent border-b-[190px] border-b-secondary opacity-60"></div>
        </div>
        <div className="absolute bottom-20 right-18">
          <div className="w-0 h-0 border-l-[140px] border-l-transparent border-b-[140px] border-b-secondary opacity-50"></div>
        </div>
        <div className="absolute bottom-40 right-36">
          <div className="w-0 h-0 border-l-[110px] border-l-transparent border-b-[110px] border-b-secondary opacity-40"></div>
        </div>
        <div className="absolute bottom-10 right-44">
          <div className="w-0 h-0 border-l-[95px] border-l-transparent border-b-[95px] border-b-secondary opacity-45"></div>
        </div>
      </div>
    </>
  );
};

export default GeometricBackground;
