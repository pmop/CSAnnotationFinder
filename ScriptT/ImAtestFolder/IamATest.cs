namespace imanamespace {
	[IamAnAttribute]
	internal class IamATest {
		public static readonly string ImAStringProportyWOAnnotations = "yeah";
		public static readonly IHaveAnnotations = null;
		[Fact]
		public string IamAnnotated {get; set;}
		
		[WithAnnotations(with="two",value="values")]
		public string AnAnnotatedMethod() {
			return IamAnnotated + " indeed";
		}
		
	}
}